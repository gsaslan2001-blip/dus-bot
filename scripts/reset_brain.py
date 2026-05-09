
"""
╔══════════════════════════════════════════════════════════════╗
║                ⚠️  MYBRAIN RESET PROTOKOLÜ  ⚠️              ║
║  BU SCRIPT GERİ DÖNÜLEMEZ VERİ KAYBINA YOL AÇAR!            ║
║  Çalıştırmadan önce --dry-run ile neyin silineceğini gör.   ║
║  Pinecone'da deletion_protection kapalı olmalı.             ║
╚══════════════════════════════════════════════════════════════╝
"""
import os
import sys
import argparse
from pinecone import Pinecone

# Güncel mybrain namespace envanteri (Gemini.MD v8.8 ile senkronize)
ALL_MYBRAIN_NAMESPACES = [
    "dus-curriculum", "dus-memory", "dus-progress",
    "dus-strategy", "dus-reference", "telos",
    "chathistory",
]

def reset_namespaces(namespaces, dry_run=False):
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY", "")
    MYBRAIN_HOST = os.environ.get("MYBRAIN_HOST", "mybrain-0crkhvy.svc.aped-4627-b74a.pinecone.io")

    if not PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY bulunamadı!")
        return

    pc = Pinecone(api_key=PINECONE_API_KEY)
    index = pc.Index(host=MYBRAIN_HOST)

    if dry_run:
        print("🔍 DRY-RUN MODU — Hiçbir veri silinmeyecek.\n")
        for ns in namespaces:
            try:
                stats = index.describe_index_stats()
                count = stats.get("namespaces", {}).get(ns, {}).get("vector_count", 0)
                print(f"  📋 {ns}: ~{count} vektör")
            except Exception as e:
                print(f"  ⚠️  {ns}: istatistik alınamadı ({e})")
        print(f"\nToplam {len(namespaces)} namespace etkilenecek.")
        return

    print("⚠️  DİKKAT: Bu işlem aşağıdaki namespace'leri TAMAMEN SİLECEKTİR:")
    for ns in namespaces:
        print(f"  🔴 {ns}")
    print(f"\nToplam {len(namespaces)} namespace GERİ DÖNÜLEMEZ şekilde silinecek.")

    confirm = input("\nDevam etmek için 'evet' yazın: ")
    if confirm.lower() != "evet":
        print("❌ İptal edildi.")
        return

    for ns in namespaces:
        try:
            print(f"🗑️  Namespace siliniyor: {ns}...")
            index.delete(delete_all=True, namespace=ns)
            print(f"✅ {ns} başarıyla temizlendi.")
        except Exception as e:
            print(f"⚠️  {ns} temizlenirken hata oluştu (belki zaten boş): {e}")

    print("\n✅ MyBrain reset tamamlandı.")

def main():
    parser = argparse.ArgumentParser(
        description="MyBrain namespace temizleme aracı (YIKICI!)",
        epilog="ÖNCE --dry-run ile kontrol et, SONRA gerçek silme yap!"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Silme yapmadan hangi namespace'lerin etkileneceğini göster")
    parser.add_argument("--ns", nargs="+", metavar="NS",
                        help=f"Hedef namespace(ler). Varsayılan: TÜM mybrain namespace'leri. Mevcut: {', '.join(ALL_MYBRAIN_NAMESPACES)}")
    args = parser.parse_args()

    namespaces = args.ns if args.ns else ALL_MYBRAIN_NAMESPACES
    unknown = [ns for ns in namespaces if ns not in ALL_MYBRAIN_NAMESPACES]
    if unknown:
        print(f"⚠️  UYARI: Bilinmeyen namespace(ler): {', '.join(unknown)}")
        print(f"   Bilinen mybrain namespace'leri: {', '.join(ALL_MYBRAIN_NAMESPACES)}")

    reset_namespaces(namespaces, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
