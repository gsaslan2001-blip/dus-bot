import os
import sys
import time
import json
import torch
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from tenacity import retry, wait_exponential, stop_after_attempt
from openai import OpenAI

# Proje kök dizinini ekle
PROJECT_DIR = Path(__file__).parent.parent
sys.path.append(str(PROJECT_DIR))

from scripts.embedding_utils import get_local_embedder

# Logging ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

# Global Client
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def parse_anki_txt(file_path):
    """Anki .txt dosyasını parse eder (GUID, Notetype, Deck, Question, Answer)."""
    cards = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 4:
                guid = parts[0].strip('"')
                notetype = parts[1]
                deck = parts[2]
                question = parts[3].strip('"')
                answer = parts[4].strip('"') if len(parts) > 4 else ""
                
                cards.append({
                    "guid": guid,
                    "notetype": notetype,
                    "deck": deck,
                    "question": question,
                    "answer": answer,
                    "vektorlenecek_metin": f"SORU: {question} CEVAP: {answer}",
                    "tokens": set(question.lower().split() + answer.lower().split())
                })
    return cards

def lexical_guard(tokens_a, tokens_b):
    """Zıtlıkları yakalamaya çalışan basit bir kural seti."""
    # Tip 1 vs Tip 2 gibi durumları koru
    for i in range(1, 5):
        t1 = f"tip {i}"
        t2 = f"tip {i+1}"
        if t1 in tokens_a and t2 in tokens_b: return False
        if t2 in tokens_a and t1 in tokens_b: return False
    
    # Anterior vs Posterior
    if ("anterior" in tokens_a and "posterior" in tokens_b) or \
       ("posterior" in tokens_a and "anterior" in tokens_b):
        return False
        
    return True

@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
async def judge_pair_with_openai(pair, sem):
    async with sem:
        prompt = f"""Aşağıdaki iki Anki kartı aynı tıbbi bilgiyi mi öğretiyor?
Eğer biri diğerini kapsıyorsa veya tamamen aynıysa 'DUPLICATE' de.
Eğer aralarında küçük ama önemli bir fark varsa 'DIFFERENT' de.

KART A:
Soru: {pair['kart_a_metin']}
Cevap: {pair['kart_a_cevap']}

KART B:
Soru: {pair['kart_b_metin']}
Cevap: {pair['kart_b_cevap']}

Yanıtın SADECE 'DUPLICATE' veya 'DIFFERENT' olsun."""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10
            )
            text = response.choices[0].message.content.strip().upper()
            pair["llm_decision"] = "DUPLIKAT" if "DUPLICATE" in text or "DUPLIKAT" in text else "FARKLI"
        except Exception as e:
            logger.error(f"OpenAI Judge Error: {e}")
            pair["llm_decision"] = "ERROR"
        
        await asyncio.sleep(0.1)

async def run_llm_judges(pairs):
    logger.info(f"{len(pairs)} şüpheli çift için OpenAI gpt-4o-mini Judge başlatılıyor...")
    sem = asyncio.Semaphore(10) # OpenAI is very stable
    tasks = [judge_pair_with_openai(p, sem) for p in pairs]
    await asyncio.gather(*tasks)

def get_anki_reps(guid):
    # Placeholder for AnkiConnect integration
    return 0

def select_card_to_delete(pair):
    """Kısa olanı tut, uzun olanı sil."""
    len_a = len(pair['kart_a_metin'])
    len_b = len(pair['kart_b_metin'])
    return pair['kart_a_guid'] if len_a > len_b else pair['kart_b_guid']

def main():
    file_path = Path(r"C:\Users\FURKAN\Desktop\Projeler\anki\endo full.txt")
    if not file_path.exists():
        logger.error(f"Dosya bulunamadı: {file_path}")
        sys.exit(1)

    cards = parse_anki_txt(file_path)
    logger.info(f"{len(cards)} kart yüklendi. Vektörleme başlıyor...")

    embedder = get_local_embedder("openai")
    vmetinler = [c["vektorlenecek_metin"] for c in cards]

    start_time = time.time()
    vectors_list = embedder.embed_batch(vmetinler)
    vectors = torch.tensor(vectors_list)
    logger.info(f"Vektörleme tamamlandı ({time.time() - start_time:.2f} saniye).")

    # Matris çarpımı ile benzerlik skorları
    sim_matrix = torch.mm(vectors, vectors.t()).cpu().numpy()

    SEMANTIC_LOW = 0.94
    candidate_pairs = []
    seen_pairs = set()

    for i in range(len(cards)):
        for j in range(i + 1, len(cards)):
            score = sim_matrix[i, j].item()
            if score >= SEMANTIC_LOW:
                guid_a = cards[i]["guid"]
                guid_b = cards[j]["guid"]
                pair_key = tuple(sorted([guid_a, guid_b]))
                if pair_key in seen_pairs: continue
                seen_pairs.add(pair_key)

                if not lexical_guard(cards[i]["tokens"], cards[j]["tokens"]): continue
                
                candidate_pairs.append({
                    "score": float(round(score, 4)),
                    "kart_a_guid": guid_a, "kart_b_guid": guid_b,
                    "kart_a_metin": cards[i]["question"], "kart_b_metin": cards[j]["question"],
                    "kart_a_cevap": cards[i]["answer"], "kart_b_cevap": cards[j]["answer"]
                })
    
    if candidate_pairs:
        asyncio.run(run_llm_judges(candidate_pairs))
    else:
        logger.info("Hiç duplikat adayı bulunamadı.")
        return

    # Raporlama
    REPORT_DIR = PROJECT_DIR / "anki_jsonlar"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    base_name = file_path.stem.replace(" ", "_")
    
    report_json = REPORT_DIR / f"{base_name}_smart_dedup_report.json"
    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(candidate_pairs, f, ensure_ascii=False, indent=2)

    report_txt = REPORT_DIR / f"{base_name}_smart_dedup_report.txt"
    to_delete_guids = []
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write(f"# SMART DEDUP REPORT: {file_path.name}\n\n")
        for idx, pair in enumerate(candidate_pairs, start=1):
            f.write(f"[{idx}] Score: {pair['score']} | Decision: {pair.get('llm_decision')}\n")
            f.write(f"  A: {pair['kart_a_metin']} -> {pair['kart_a_cevap']}\n")
            f.write(f"  B: {pair['kart_b_metin']} -> {pair['kart_b_cevap']}\n")
            if pair.get("llm_decision") == "DUPLIKAT":
                del_guid = select_card_to_delete(pair)
                to_delete_guids.append(del_guid)
                f.write(f"  >>> DELETE: {del_guid}\n")
            f.write("-" * 50 + "\n")

    with open(REPORT_DIR / f"{base_name}_to_delete.txt", "w", encoding="utf-8") as f:
        for g in set(to_delete_guids): f.write(f"{g}\n")

    logger.info(f"Analiz tamamlandı. Rapor: {report_txt}")

if __name__ == "__main__":
    main()
