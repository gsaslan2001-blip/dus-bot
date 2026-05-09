"""Hızlı 5 çift testi — max_tokens düzeltmesini doğrula."""
import os, json, re, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI

base_url = os.environ.get("DEEPSEEK_BASE_URL")
api_key = os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY"))
model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")
client = OpenAI(api_key=api_key, base_url=base_url)

with open("anki_jsonlar/deneme_analizi_internal_dedup_report.json", "r", encoding="utf-8") as f:
    all_pairs = json.load(f)

pairs = [p for p in all_pairs if p.get("score", 0) >= 0.84][:5]
print(f"Test edilecek cift: {len(pairs)}")

for i, pair in enumerate(pairs):
    prompt = (
        "DUPLIKAT mi? KISA YANIT:\n"
        f"KART A: {pair.get('kart_a_baslik','')} | {pair.get('kart_a_metin','')[:120]}\n"
        f"KART B: {pair.get('kart_b_baslik','')} | {pair.get('kart_b_metin','')[:120]}\n\n"
        "Sadece su formatta:\n"
        "KARAR: DUPLIKAT veya FARKLI\n"
        "GEREKCE: 1 cumle"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=4000,
        temperature=0.0,
    )
    raw = (resp.choices[0].message.content or "").strip()
    finish = resp.choices[0].finish_reason
    reasoning = getattr(
        getattr(resp.usage, "completion_tokens_details", None), "reasoning_tokens", 0
    ) or 0
    karar_m = re.search(r"KARAR[:\s]+(DUPLIKAT|FARKLI)", raw, re.IGNORECASE)
    score = pair.get("score", 0)
    karar_str = karar_m.group(1) if karar_m else "PARSE_HATA"
    print(
        f"[{i+1}] score={score:.4f} | finish={finish} | reasoning={reasoning}tok "
        f"| KARAR={karar_str} | raw_len={len(raw)}"
    )
    if karar_m:
        print(f"      RAW: {raw[:200]}")
    else:
        print(f"      FAIL RAW: {raw!r}")
