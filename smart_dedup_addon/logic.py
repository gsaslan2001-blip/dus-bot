import os
import json
import urllib.request
import urllib.error
import math
from aqt import mw

class SmartDedupLogic:
    def __init__(self, api_key, threshold=0.88):
        self.api_key = api_key
        self.threshold = threshold
        self.api_url = "https://api.openai.com/v1/embeddings"

    def get_cards_from_deck(self, deck_name):
        """Destedeki kartları çeker."""
        query = f'deck:"{deck_name}"'
        note_ids = mw.col.find_notes(query)
        
        extracted_data = []
        for nid in note_ids:
            try:
                note = mw.col.get_note(nid)
                model_name = note.model()['name']
                
                card_ids = mw.col.db.list(f"select id from cards where nid = {nid}")
                if not card_ids: continue
                
                card = mw.col.get_card(card_ids[0])
                status = "Yeni" if card.queue == 0 else f"Çalışılıyor (Ivl: {card.ivl} gün)"
                
                fields = note.keys()
                if "cloze" in model_name.lower():
                    text_field = next((f for f in fields if f.lower() in ["text", "metin"]), fields[0])
                    text_to_vector = note[text_field]
                    display_q = note[text_field]
                    display_a = "(Cloze)"
                else:
                    front_field = next((f for f in fields if f.lower() in ["front", "soru", "ön"]), fields[0])
                    back_field = next((f for f in fields if f.lower() in ["back", "cevap", "arka"]), fields[1] if len(fields)>1 else fields[0])
                    text_to_vector = f"{note[front_field]} {note[back_field]}"
                    display_q = note[front_field]
                    display_a = note[back_field]

                extracted_data.append({
                    "nid": nid, "guid": note.guid, "text_to_vector": text_to_vector,
                    "display_question": display_q, "display_answer": display_a,
                    "status": status, "reps": card.reps
                })
            except Exception: continue
            
        return extracted_data

    def get_embeddings(self, texts):
        """OpenAI API çağrısı (urllib ile bağımsız çalışma)."""
        all_embeddings = []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        for i in range(0, len(texts), 100):
            batch = texts[i:i+100]
            payload = json.dumps({
                "model": "text-embedding-3-large",
                "input": batch,
                "dimensions": 3072
            }).encode("utf-8")
            
            req = urllib.request.Request(self.api_url, data=payload, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    all_embeddings.extend([item["embedding"] for item in res_data["data"]])
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                raise Exception(f"OpenAI HTTP Hatası: {e.code} - {error_body}")
            except Exception as e:
                raise Exception(f"Bağlantı Hatası: {str(e)}")
                
        return all_embeddings

    def find_duplicates(self, cards, embeddings, progress_callback=None):
        """Doğrudan tam vektör karşılaştırması."""
        num_cards = len(cards)
        norm_embeddings = []
        for v in embeddings:
            mag = math.sqrt(sum(x*x for x in v))
            norm_embeddings.append([x/mag for x in v] if mag > 0 else v)
        
        pairs = []
        total_steps = (num_cards * (num_cards - 1)) // 2
        current_step = 0
        
        for i in range(num_cards):
            v1 = norm_embeddings[i]
            for j in range(i + 1, num_cards):
                current_step += 1
                if current_step % 10000 == 0 and progress_callback:
                    progress_callback(current_step, total_steps)
                
                v2 = norm_embeddings[j]
                score = sum(a * b for a, b in zip(v1, v2))
                
                if score >= self.threshold:
                    pairs.append((cards[i], cards[j], float(score)))
        
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs
