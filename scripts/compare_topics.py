import asyncio
import sys
import os
import argparse
from google import genai
from google.genai import types

# Scripts klasörünü path'e ekle
sys.path.append(os.path.dirname(__file__))
from search_engine import async_pinecone_search
from config import GEMINI_API_KEY, GEMINI_MODELS

async def generate_comparison(topic1, topic2, context1, context2):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
Sen bir DUS (Diş Hekimliğinde Uzmanlık Sınavı) eğitmenisin. 
Aşağıda iki farklı konu hakkında toplanan ders notu parçaları bulunmaktadır. 

Konu 1: {topic1}
Konu 2: {topic2}

Senden isteğim:
1. Bu iki konuyu karşılaştıran profesyonel bir "Ayırıcı Tanı Matrisi" (Tablo) oluşturman.
2. Tabloda; Tanım, Klinik Özellikler, Radyoloji, Histopatoloji ve Tedavi gibi ana başlıklar olsun.
3. Tablo altına, DUS'ta çıkabilecek kritik farkları "High-Yield Notlar" olarak ekle.

NOTLAR (Konu 1 - {topic1}):
{context1}

NOTLAR (Konu 2 - {topic2}):
{context2}

Lütfen yanıtı Markdown formatında ve Türkçe ver.
"""

    # Retry logic for models
    last_error = None
    for model_name in GEMINI_MODELS:
        try:
            # Gemini client call can be run in executor if it blocks, 
            # but genai library is typically okay.
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            last_error = e
            continue
    
    return f"Hata oluştu: {last_error}"

async def main():
    parser = argparse.ArgumentParser(description="İki DUS konusunu karşılaştırır.")
    parser.add_argument("topic1", help="Birinci konu (örn: Radiküler Kist)")
    parser.add_argument("topic2", help="İkinci konu (örn: Dentigeröz Kist)")
    parser.add_argument("--namespace", default="patoloji", help="Pinecone namespace (varsayılan: patoloji)")
    parser.add_argument("--top_k", type=int, default=10, help="Her konu için çekilecek parça sayısı")
    
    args = parser.parse_args()
    
    print(f"\n🔍 '{args.topic1}' ve '{args.topic2}' karşılaştırılıyor (Paralel Sorgu)...")
    
    # Topic 1 ve Topic 2 Arama - PARALEL
    print(f"📡 Veriler paralel olarak getiriliyor...")
    
    tasks = [
        async_pinecone_search(args.topic1, "myppdfs", args.namespace, top_k=args.top_k * 2, rerank_top_n=args.top_k),
        async_pinecone_search(args.topic2, "myppdfs", args.namespace, top_k=args.top_k * 2, rerank_top_n=args.top_k)
    ]
    
    results = await asyncio.gather(*tasks)
    results1, results2 = results
    
    context1 = "\n---\n".join(results1)
    context2 = "\n---\n".join(results2)
    
    if not results1 and not results2:
        print("❌ Her iki konu için de veri bulunamadı.")
        return

    print("🧠 Gemini ile karşılaştırma matrisi oluşturuluyor...")
    comparison = await generate_comparison(args.topic1, args.topic2, context1, context2)
    
    print("\n" + "="*50)
    print(comparison)
    print("="*50 + "\n")
    
    # Sonucu bir dosyaya da kaydedelim
    filename = f"comparison_{args.topic1.replace(' ', '_')}_vs_{args.topic2.replace(' ', '_')}.md"
    output_path = os.path.join(os.getcwd(), "RAPORLAR", filename)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(comparison)
    
    print(f"💾 Rapor kaydedildi: {output_path}")

if __name__ == "__main__":
    asyncio.run(main())
