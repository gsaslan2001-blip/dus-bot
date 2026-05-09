import os
import json
import time
import hashlib
import urllib.request
import urllib.error
import math
import re
try:
    import numpy as np
except ImportError:
    np = None
from aqt import mw
from anki.utils import strip_html

CACHE_VERSION = 2


class SmartDedupLogic:
    OPENAI_API_URL = "https://api.openai.com/v1/embeddings"

    def __init__(self, api_key, threshold=0.84, allowed_models=None):
        self.api_key = api_key
        self.threshold = threshold
        self.api_url = self.OPENAI_API_URL
        self.cache = {}
        self.current_ns = None
        self.allowed_models = allowed_models or ["cloze-maxx", "basic-anking"]

    # ── Cache ─────────────────────────────────────────────────────────────────

    def get_cache_path(self, ns_name):
        # Namespace standardı: Küçük harf ve sadece güvenli karakterler.
        # ui.py ile birebir aynı regex'i kullanıyoruz.
        ns_name = ns_name.lower()
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", ns_name)[:100]
        return os.path.join(os.path.dirname(__file__), f"{safe}.json")

    @staticmethod
    def _text_hash(text):
        """8-char MD5 prefix — detects stale embeddings when note content changes."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]

    def load_cache(self, ns_name):
        if self.current_ns == ns_name and self.cache is not None:
            return self.cache

        path = self.get_cache_path(ns_name)
        self.current_ns = ns_name
        self.cache = {}

        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("_version") == CACHE_VERSION:
                    self.cache = {k: v for k, v in data.items() if k != "_version"}
                # v1 format (raw lists) silently discarded → re-vectorize everything
            except (json.JSONDecodeError, OSError, ValueError) as e:
                print(f"[SmartDedup] Önbellek yüklenirken hata ({path}): {e}")
                self.cache = {}

        return self.cache

    def save_cache(self, ns_name, new_data):
        """Merge new_data into in-memory cache and flush to disk atomically."""
        if self.current_ns != ns_name:
            self.load_cache(ns_name)

        self.cache.update(new_data)

        path = self.get_cache_path(ns_name)
        tmp_path = path + ".tmp"
        try:
            payload = {"_version": CACHE_VERSION}
            payload.update(self.cache)
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
            os.replace(tmp_path, path)  # atomic on all platforms
        except (OSError, IOError) as e:
            print(f"[SmartDedup] Önbellek kaydedilemedi ({path}): {e}")
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    # ── Anki DB (main thread only) ────────────────────────────────────────────

    def get_cards_from_deck(self, deck_name):
        query = f'deck:"{deck_name}"'
        note_ids = mw.col.find_notes(query)

        extracted = []
        for nid in note_ids:
            try:
                note = mw.col.get_note(nid)
                model_name = note.model()["name"]

                if not any(m in model_name.lower() for m in self.allowed_models):
                    continue

                card_ids = mw.col.db.list(f"select id from cards where nid = {nid}")
                if not card_ids:
                    continue

                card = mw.col.get_card(card_ids[0])
                status = "Yeni" if card.queue == 0 else f"Çalışılıyor (Ivl: {card.ivl} gün)"

                fields = note.keys()
                if "cloze" in model_name.lower():
                    text_field = next(
                        (f for f in fields if f.lower() in ["text", "metin"]), fields[0]
                    )
                    text_to_vector = note[text_field]
                    display_q = note[text_field]
                    display_a = "(Cloze)"
                else:
                    front_field = next(
                        (f for f in fields if f.lower() in ["front", "soru", "ön"]), fields[0]
                    )
                    back_field = next(
                        (f for f in fields if f.lower() in ["back", "cevap", "arka"]),
                        fields[1] if len(fields) > 1 else fields[0],
                    )
                    text_to_vector = f"{note[front_field]} {note[back_field]}"
                    display_q = note[front_field]
                    display_a = note[back_field]

                text_to_vector = strip_html(text_to_vector).strip()
                text_to_vector = re.sub(r"\{\{c\d+::(.*?)(::.*?)?\}\}", r"\1", text_to_vector)

                if not text_to_vector:
                    continue

                unit_name = deck_name.split("::", 1)[1] if "::" in deck_name else deck_name

                extracted.append(
                    {
                        "nid": nid,
                        "guid": note.guid,
                        "text_to_vector": text_to_vector,
                        "display_question": display_q,
                        "display_answer": display_a,
                        "status": status,
                        "reps": int(card.reps),
                        "ivl": int(card.ivl),
                        "lapses": int(card.lapses),
                        "factor": int(card.factor),
                        "due": int(card.due),
                        "last_mod": int(note.mod),
                        "tags": ", ".join(note.tags),
                        "model_name": model_name,
                        "deck_name": deck_name,
                        "unit_name": unit_name,
                    }
                )
            except Exception as e:
                print(f"[SmartDedup] Kart {nid} atlandı: {e}")
                continue

        return extracted

    # ── OpenAI (background thread) ────────────────────────────────────────────

    def get_embeddings(self, texts, progress_callback=None):
        """Batch embed with 3-retry exponential backoff per batch."""
        all_embeddings = []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        total_batches = math.ceil(len(texts) / 100)

        for batch_num, i in enumerate(range(0, len(texts), 100)):
            batch = texts[i : i + 100]
            payload = json.dumps(
                {"model": "text-embedding-3-large", "input": batch, "dimensions": 3072}
            ).encode("utf-8")

            for attempt in range(3):
                if attempt > 0:
                    time.sleep(2 ** attempt)  # 2 s, 4 s

                req = urllib.request.Request(
                    self.api_url, data=payload, headers=headers, method="POST"
                )
                try:
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        all_embeddings.extend(
                            [item["embedding"] for item in res_data["data"]]
                        )
                    break  # success → next batch
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8")
                    if e.code in (429, 500, 502, 503) and attempt < 2:
                        continue
                    raise Exception(f"OpenAI HTTP {e.code}: {body}")
                except (urllib.error.URLError, OSError, TimeoutError) as e:
                    if attempt < 2:
                        continue
                    raise Exception(f"Bağlantı hatası (3 denemeden sonra): {e}")

            if progress_callback:
                progress_callback(batch_num + 1, total_batches)

        return all_embeddings

    # ── Similarity (background thread) ───────────────────────────────────────

    def find_duplicates(self, cards, embeddings, progress_callback=None):
        num_cards = len(cards)
        if num_cards < 2:
            return []

        if np is None:
            return self._find_duplicates_slow(cards, embeddings, progress_callback)

        vecs = np.array(embeddings, dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        vecs = vecs / norms

        pairs = []
        # CHUNK rows at a time → max memory: CHUNK × N × 4 bytes
        # N=10k → 2000×10000×4 = 80 MB peak (vs 400 MB for full matrix)
        CHUNK = 2000
        total_chunks = math.ceil(num_cards / CHUNK)

        for chunk_idx, start in enumerate(range(0, num_cards, CHUNK)):
            end = min(start + CHUNK, num_cards)
            chunk_sim = np.dot(vecs[start:end], vecs.T)  # (CHUNK, N) float32

            rows, cols = np.where(chunk_sim >= self.threshold)
            for r, c in zip(rows, cols):
                global_i = start + int(r)
                card_a = cards[global_i]
                card_b = cards[int(c)]
                if global_i < int(c):
                    if self._lexical_guard(card_a, card_b):
                        pairs.append((card_a, card_b, float(chunk_sim[r, c])))

            del chunk_sim  # release CHUNK×N block immediately

            if progress_callback:
                progress_callback(chunk_idx + 1, total_chunks)

        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs

    def _find_duplicates_slow(self, cards, embeddings, progress_callback=None):
        num_cards = len(cards)
        norm_embs = []
        for v in embeddings:
            mag = math.sqrt(sum(x * x for x in v))
            norm_embs.append([x / mag for x in v] if mag > 0 else v)

        pairs = []
        total = (num_cards * (num_cards - 1)) // 2
        step = 0
        for i in range(num_cards):
            v1 = norm_embs[i]
            for j in range(i + 1, num_cards):
                step += 1
                if progress_callback and step % 10000 == 0:
                    progress_callback(step, total)
                score = sum(a * b for a, b in zip(v1, norm_embs[j]))
                if score >= self.threshold:
                    if self._lexical_guard(cards[i], cards[j]):
                        pairs.append((cards[i], cards[j], float(score)))

        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs

    def _lexical_guard(self, card_a, card_b):
        """Quickly discard pairs that are obviously different (e.g. Tip 1 vs Tip 2)."""
        text_a = card_a["text_to_vector"].lower()
        text_b = card_b["text_to_vector"].lower()

        # Tip / Evre / Sınıf / Faz differences
        patterns = [r"\btip\s*(\d+|[ivx]+)\b", r"\bevre\s*(\d+|[ivx]+)\b", 
                    r"\bsınıf\s*(\d+|[ivx]+)\b", r"\bfaz\s*(\d+|[ivx]+)\b",
                    r"\bgrade\s*(\d+|[ivx]+)\b", r"\bstage\s*(\d+|[ivx]+)\b"]
        
        for p in patterns:
            m_a = re.search(p, text_a)
            m_b = re.search(p, text_b)
            if m_a and m_b and m_a.group(1) != m_b.group(1):
                return False
        
        # Binary opposites
        opposites = [("anterior", "posterior"), ("distal", "proksimal"), 
                     ("artır", "azalt"), ("hiper", "hipo"), 
                     ("sempatik", "parasempatik")]
        for opt1, opt2 in opposites:
            if (opt1 in text_a and opt2 in text_b) or (opt2 in text_a and opt1 in text_b):
                return False
                
        return True


    # ── Pinecone (background thread) ─────────────────────────────────────────

    def upsert_to_pinecone(self, cards, embeddings, pc_api_key, pc_host, namespace):
        url = f"https://{pc_host}/vectors/upsert"
        headers = {"Api-Key": pc_api_key, "Content-Type": "application/json"}

        vectors = [
            {
                "id": card["guid"],
                "values": embeddings[i],
                "metadata": {
                    "text": card["text_to_vector"],
                    "nid": str(card["nid"]),
                    "status": card["status"],
                    "tags": card["tags"],
                    "model_name": card["model_name"],
                    "deck_name": card["deck_name"],
                    "unit": card["unit_name"],
                    "reps": int(card["reps"]),
                    "ivl": int(card["ivl"]),
                    "lapses": int(card["lapses"]),
                    "factor": int(card["factor"]),
                    "due": int(card["due"]),
                    "last_mod": int(card["last_mod"]),
                },
            }
            for i, card in enumerate(cards)
        ]

        total_batches = math.ceil(len(vectors) / 100)
        for batch_num, i in enumerate(range(0, len(vectors), 100)):
            batch = vectors[i : i + 100]
            payload = json.dumps({"vectors": batch, "namespace": namespace}).encode("utf-8")

            for attempt in range(3):
                if attempt > 0:
                    time.sleep(2 ** attempt)
                req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=30):
                        pass
                    break
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8")
                    if e.code in (429, 500, 502, 503) and attempt < 2:
                        continue
                    raise Exception(f"Pinecone HTTP {e.code}: {body}")
                except (urllib.error.URLError, OSError, TimeoutError) as e:
                    if attempt < 2:
                        continue
                    raise Exception(f"Pinecone bağlantı hatası (3 deneme): {e}")

    def get_pinecone_namespaces(self, pc_api_key, pc_host):
        url = f"https://{pc_host}/describe_index_stats"
        headers = {"Api-Key": pc_api_key}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return list(data.get("namespaces", {}).keys())
        except Exception as e:
            print(f"[SmartDedup] Pinecone namespace listesi alınamadı: {e}")
            return []

    def pull_from_pinecone(self, ns_name, pc_api_key, pc_host, progress_callback=None):
        """
        Pinecone'daki tüm vektörleri çekip yerel cache'e kaydeder.
        Böylece tekrar vektörleme maliyetinden kurtuluruz.
        """
        # 1. Tüm ID'leri listele
        all_ids = []
        next_token = ""
        
        list_url_base = f"https://{pc_host}/vectors/list?namespace={ns_name}"
        headers = {"Api-Key": pc_api_key}
        
        while True:
            url = list_url_base
            if next_token:
                url += f"&paginationToken={next_token}"

            req = urllib.request.Request(url, headers=headers, method="GET")
            last_err = None
            for attempt in range(3):
                if attempt > 0:
                    time.sleep(2 ** attempt)
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        vectors = data.get("vectors", [])
                        all_ids.extend([v["id"] for v in vectors])
                        next_token = data.get("pagination", {}).get("next")
                        last_err = None
                        break
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8")
                    last_err = f"Pinecone HTTP {e.code}: {body}"
                    if e.code in (429, 500, 502, 503) and attempt < 2:
                        continue
                    raise Exception(last_err)
                except Exception as e:
                    last_err = str(e)
                    if attempt < 2:
                        continue
                    raise Exception(f"ID listeleme hatası (3 deneme): {last_err}")
            if last_err:
                raise Exception(last_err)
            if not next_token:
                break

        if not all_ids:
            return 0

        # 2. Fetch ile vektörleri çek (100'erli batch)
        fetch_url = f"https://{pc_host}/vectors/fetch?namespace={ns_name}"
        new_cache_data = {}
        total_batches = math.ceil(len(all_ids) / 100)
        
        for batch_num, i in enumerate(range(0, len(all_ids), 100)):
            batch = all_ids[i : i + 100]
            ids_str = "&ids=" + "&ids=".join(batch)
            url = fetch_url + ids_str
            
            req = urllib.request.Request(url, headers=headers, method="GET")
            for attempt in range(3):
                if attempt > 0:
                    time.sleep(2 ** attempt)
                try:
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        vectors_data = res_data.get("vectors", {})
                        for vid, vec_info in vectors_data.items():
                            meta = vec_info.get("metadata", {})
                            text = meta.get("text", "")
                            h = self._text_hash(text) if text else "stale"
                            new_cache_data[vid] = {
                                "h": h,
                                "emb": vec_info.get("values", [])
                            }
                    break
                except urllib.error.HTTPError as e:
                    body = e.read().decode("utf-8")
                    if e.code in (429, 500, 502, 503) and attempt < 2:
                        continue
                    raise Exception(f"Pinecone fetch HTTP {e.code}: {body}")
                except Exception as e:
                    if attempt < 2:
                        continue
                    raise Exception(f"Vektör çekme hatası (3 deneme): {e}")
            
            if progress_callback:
                progress_callback(batch_num + 1, total_batches)

        if new_cache_data:
            self.save_cache(ns_name, new_cache_data)
        
        return len(new_cache_data)
