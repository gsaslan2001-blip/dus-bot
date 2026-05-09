"""
run_death_match.py — DUS Mentörü Ölüm Maçı Motoru v2.1
===========================================================
Yargıç: DeepSeek V4 Pro (deepseek-v4-pro) — DEEPSEEK_MODEL env ile override.

ÖNEMLİ: deepseek-v4-pro bir Reasoning (Thinking) modelidir. Her yanıtta görünmez iç düşünme
(reasoning_tokens) için token harcar. max_tokens çok düşük ayarlanırsa tüm bütçe
reasoning'e gider ve gerçek yanıt için 0 token kalır → boş string döner.
Bu nedenle max_tokens en az 4000 olmalıdır (tipik: reasoning ~700 + yanıt ~100).
Çıktı 1: {stem}_death_match_raporu.md      — Markdown karar raporu
Çıktı 2: {stem}_death_match_results.json   — Kararlar JSON (resume/retry için)
Çıktı 3: {ders}_{unite}_temiz.txt          — Anki import-ready (TAB-separated Cloze-MAXXİNG)

Kullanım:
    python scripts/run_death_match.py \
        --report anki_jsonlar/radyoloji_artefakt_internal_dedup_report.json \
        --original-json anki_jsonlar/radyoloji_artefakt.json \
        [--threshold 0.84] [--concurrency 3]

    # Sadece hatalı çiftleri yeniden çalıştır:
    python scripts/run_death_match.py \
        --report anki_jsonlar/radyoloji_artefakt_internal_dedup_report.json \
        --retry-errors
"""

import os
import re
import json
import asyncio
import logging
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from tenacity import retry, wait_exponential, stop_after_attempt

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# ── Env & Client ─────────────────────────────────────────────────────────────
load_dotenv()

_base_url = os.environ.get("DEEPSEEK_BASE_URL")
if _base_url:
    openai_client = OpenAI(
        api_key=os.environ.get("DEEPSEEK_API_KEY", os.environ.get("OPENAI_API_KEY")),
        base_url=_base_url,
    )
else:
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro")

# deepseek-v4-pro reasoning modelidir: iç düşünme ~700 token + yanıt ~100 token
# max_tokens=400 → reasoning tüm bütçeyi tüketir, gerçek yanıt için 0 token kalır!
MAX_TOKENS = int(os.environ.get("DEEPSEEK_MAX_TOKENS", "8000"))

# ── Prompt Template ───────────────────────────────────────────────────────────
JUDGE_PROMPT = """\
Sen bir DUS (Diş Hekimliği Uzmanlık Sınavı) soru bankası kalite yargıcısın.

GÖREV: Aşağıdaki iki Anki kartının aynı tıbbi/dental bilgiyi öğretip öğretmediğini belirle.

===KURAL SETİ (KESİN)===
[1] LEXICAL GUARD — Aşağıdaki çiftler HER ZAMAN FARKLI kabul edilir (mutlak kural):
    - Açık çıkma vs Koyu çıkma
    - Birinci banyo vs İkinci banyo (farklı etki/sonuç)
    - Siyah leke vs Beyaz leke
    - Artmak vs Azalmak
    - Evre I vs Evre II (veya III, IV)
    - Faz 1 vs Faz 2
    - Geliştirici vs Fiksaj

[2] DUPLIKAT SAYILMA ŞARTLARI (HER İKİSİ SAĞLANMALI):
    - Aynı klinik gerçeği öğretiyor VE
    - Biri diğerini tamamen kapsıyor (superset) VEYA kelime düzeyinde yeniden ifade (paraphrase) — pedagojik fark yok
    - NOT: Aynı bilgiyi farklı sormak da DUPLIKAT'tır.

[3] FARKLI SAYILMA ŞARTLARI (BİRİ YETERLİ):
    - Farklı mekanizma, etiyoloji veya klinik sonuç
    - Bir kart diğerinde olmayan ek klinik bilgi içeriyor
    - LEXICAL GUARD kapsamında (bkz. [1])

[4] KART KALİTESİ DEĞERLENDİRMESİ (sadece DUPLIKAT kararında):
    Daha iyi kartı KORUNAN olarak seç. Tercih sırası:
    a) İçinde Extra/bağlam bilgisi olan kart
    b) Cloze boşlukları daha net ve spesifik olan kart
    c) Daha kapsamlı (superset) olan kart
    d) Daha uzun ve bilgi yoğun metin

===KARAR FORMATI (KESİN UYULACAK)===
DUPLIKAT kararında:
KARAR: DUPLIKAT
KORUNAN: A
ELENEN: B
GEREKÇE: [1-2 cümle teknik açıklama]

FARKLI kararında:
KARAR: FARKLI
GEREKÇE: [1-2 cümle teknik açıklama]

===KARTLAR===
KART A:
Başlık: {baslik_a}
Metin  : {metin_a}

KART B:
Başlık: {baslik_b}
Metin  : {metin_b}
"""

# ── Judge ─────────────────────────────────────────────────────────────────────
@retry(wait=wait_exponential(multiplier=1, min=4, max=30), stop=stop_after_attempt(4))
async def judge_pair(pair: dict, sem: asyncio.Semaphore) -> None:
    """DeepSeek'e çift gönder, kararı parse et ve pair dict'e yaz."""
    async with sem:
        prompt = JUDGE_PROMPT.format(
            baslik_a=pair.get("kart_a_baslik", ""),
            metin_a=pair.get("kart_a_metin", ""),
            baslik_b=pair.get("kart_b_baslik", ""),
            metin_b=pair.get("kart_b_metin", ""),
        )

        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: openai_client.chat.completions.create(
                    model=MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=MAX_TOKENS,  # Reasoning model: iç düşünme ~700 + yanıt ~100 token
                    temperature=0.0,
                ),
            )
            choice = response.choices[0]
            raw = (choice.message.content or "").strip()
            finish_reason = choice.finish_reason

            # Tanısal loglama: reasoning model token kullanımını izle
            usage = response.usage
            reasoning_tokens = getattr(
                getattr(usage, "completion_tokens_details", None),
                "reasoning_tokens", 0
            ) or 0
            logger.debug(
                f"guid_a={pair.get('kart_a_guid')} | finish={finish_reason} "
                f"| reasoning={reasoning_tokens} | total={usage.total_tokens if usage else '?'}"
            )

            # Boş yanıt kontrolü — reasoning tüm token'ı tükettiyse retry
            if not raw:
                logger.warning(
                    f"Boş yanıt! finish={finish_reason}, reasoning_tokens={reasoning_tokens}. "
                    f"guid_a={pair.get('kart_a_guid')}. MAX_TOKENS artırılabilir."
                )
                raise ValueError(f"Boş API yanıtı (finish={finish_reason}, reasoning={reasoning_tokens})")

            _parse_response(pair, raw)

        except Exception as e:
            # tenacity retry'ı bu exception'ı yakalayacak (stop_after_attempt'e kadar)
            # Son denemede pair'i ERROR olarak işaretle
            if "Boş API yanıtı" not in str(e):
                logger.error(f"Judge Error (guid_a={pair.get('kart_a_guid')}): {e}")
            pair["llm_decision"] = "ERROR"
            pair["llm_korunan"] = None
            pair["llm_elenen"] = None
            pair["llm_gerekce"] = str(e)
            raise  # tenacity'nin retry yapabilmesi için re-raise

        await asyncio.sleep(0.1)


def _parse_response(pair: dict, raw: str) -> None:
    """Model yanıtını regex ile parse et."""
    # Esnek regex: KARAR: DUPLIKAT, KARAR DUPLIKAT, **KARAR**: DUPLIKAT, vb.
    karar_match = re.search(r"\*{0,2}KARAR\*{0,2}\s*[:\-]?\s*(DUPLIKAT|FARKLI)", raw, re.IGNORECASE)
    korunan_match = re.search(r"\*{0,2}KORUNAN\*{0,2}\s*[:\-]?\s*([AB])", raw, re.IGNORECASE)
    elenen_match = re.search(r"\*{0,2}ELENEN\*{0,2}\s*[:\-]?\s*([AB])", raw, re.IGNORECASE)
    gerekce_match = re.search(
        r"\*{0,2}GEREK[CÇ]E\*{0,2}\s*[:\-]?\s*(.+)",
        raw, re.IGNORECASE | re.DOTALL
    )

    if not karar_match:
        # Ham yanıtın tamamını kaydet (hata analizi için)
        logger.warning(f"Parse hatası! Ham yanıt (ilk 300): {raw[:300]!r}")
        pair["llm_decision"] = "ERROR"
        pair["llm_korunan"] = None
        pair["llm_elenen"] = None
        pair["llm_gerekce"] = f"Parse hatası. Ham yanıt: {raw[:300]}"
        return

    karar = karar_match.group(1).upper()
    pair["llm_decision"] = karar
    pair["llm_gerekce"] = gerekce_match.group(1).strip() if gerekce_match else ""

    if karar == "DUPLIKAT":
        korunan = korunan_match.group(1).upper() if korunan_match else None
        elenen = elenen_match.group(1).upper() if elenen_match else None

        # Fallback: model KORUNAN belirtmediyse kalite-bazlı seçim
        if korunan is None:
            korunan = _quality_based_select(pair)
            elenen = "B" if korunan == "A" else "A"
            pair["llm_gerekce"] += " [Fallback: kalite-bazlı seçim uygulandı]"

        pair["llm_korunan"] = korunan
        pair["llm_elenen"] = elenen

        # GUID çözümle
        if korunan == "A":
            pair["korunan_guid"] = pair["kart_a_guid"]
            pair["elenen_guid"] = pair["kart_b_guid"]
        else:
            pair["korunan_guid"] = pair["kart_b_guid"]
            pair["elenen_guid"] = pair["kart_a_guid"]
    else:
        pair["llm_korunan"] = None
        pair["llm_elenen"] = None
        pair["korunan_guid"] = None
        pair["elenen_guid"] = None


def _quality_based_select(pair: dict) -> str:
    """
    Fallback: Kalite kriterleri ile hangi kartın korunacağını belirle.
    Öncelik: extra alanı > cloze boşluk sayısı > metin uzunluğu.
    """
    # Bu fonksiyon pair dict'e erişimi var ama original JSON haritasına erişimi yok.
    # Bu nedenle metin uzunluğuna dayalı basit fallback kullanıyoruz.
    len_a = len(pair.get("kart_a_metin", ""))
    len_b = len(pair.get("kart_b_metin", ""))
    return "A" if len_a >= len_b else "B"


async def run_all_judges(pairs: list[dict], concurrency: int) -> None:
    logger.info(
        f"{len(pairs)} çift için DeepSeek [{MODEL}] yargılaması başlıyor... "
        f"(concurrency={concurrency}, max_tokens={MAX_TOKENS})"
    )
    sem = asyncio.Semaphore(concurrency)
    # gather yerine as_completed benzeri ilerleme için tasks ayrı yönet
    tasks = [judge_pair(p, sem) for p in pairs]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Exception'ları say (tenacity sonrası hâlâ başarısız olanlar)
    exceptions = [r for r in results if isinstance(r, Exception)]
    if exceptions:
        logger.warning(f"{len(exceptions)} çift tenacity sonrası da başarısız.")
    logger.info("Tüm yargılamalar tamamlandı.")


# ── Markdown Raporu ───────────────────────────────────────────────────────────
def write_markdown_report(
    pairs: list[dict],
    json_path: Path,
    threshold: float,
    output_path: Path,
) -> None:
    duplikat = [p for p in pairs if p.get("llm_decision") == "DUPLIKAT"]
    farkli = [p for p in pairs if p.get("llm_decision") == "FARKLI"]
    error = [p for p in pairs if p.get("llm_decision") == "ERROR"]

    tarih = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# ⚔️ Ölüm Maçı Raporu — DeepSeek V4 Pro",
        f"**Kaynak:** {json_path.name}  ",
        f"**Tarih:** {tarih} | **Model:** {MODEL} | **Eşik:** {threshold}",
        "",
        "## 📊 Özet",
        f"- Değerlendirilen çift: **{len(pairs)}**",
        f"- Duplikat (elenen): **{len(duplikat)}**",
        f"- Farklı (korunan çift): **{len(farkli)}**",
        f"- Hata: **{len(error)}**",
        "",
        "---",
        "",
    ]

    for idx, pair in enumerate(pairs, start=1):
        decision = pair.get("llm_decision", "ERROR")
        score = pair.get("score", "?")
        gerekce = pair.get("llm_gerekce", "")

        if decision == "FARKLI":
            lines.append(f"## [{idx}] Score: {score} | ✅ FARKLI")
            lines.append("")
            lines.append("| | Kart A | Kart B |")
            lines.append("|---|---|---|")
            lines.append(f"| **Başlık** | {pair.get('kart_a_baslik', '')} | {pair.get('kart_b_baslik', '')} |")
            lines.append(f"| **Metin** | {_truncate(pair.get('kart_a_metin', ''))} | {_truncate(pair.get('kart_b_metin', ''))} |")
            lines.append("")
            lines.append(f"**Gerekçe:** {gerekce}")
            lines.append("")
            lines.append("---")
            lines.append("")

        elif decision == "DUPLIKAT":
            korunan = pair.get("llm_korunan", "?")
            elenen = pair.get("llm_elenen", "?")
            korunan_metin = pair.get(f"kart_{korunan.lower()}_metin", "") if korunan in ("A", "B") else ""
            elenen_metin = pair.get(f"kart_{elenen.lower()}_metin", "") if elenen in ("A", "B") else ""
            korunan_baslik = pair.get(f"kart_{korunan.lower()}_baslik", "") if korunan in ("A", "B") else ""
            elenen_baslik = pair.get(f"kart_{elenen.lower()}_baslik", "") if elenen in ("A", "B") else ""
            korunan_guid = pair.get("korunan_guid", "?")
            elenen_guid = pair.get("elenen_guid", "?")

            lines.append(f"## [{idx}] Score: {score} | ❌ DUPLIKAT")
            lines.append("")
            lines.append(f"| | Korunan (Kart {korunan}) | Elenen (Kart {elenen}) |")
            lines.append("|---|---|---|")
            lines.append(f"| **Başlık** | {korunan_baslik} | {elenen_baslik} |")
            lines.append(f"| **Metin** | {_truncate(korunan_metin)} | {_truncate(elenen_metin)} |")
            lines.append(f"| **GUID** | `{korunan_guid}` | `{elenen_guid}` |")
            lines.append("")
            lines.append(f"**Gerekçe:** {gerekce}")
            lines.append("")
            lines.append("---")
            lines.append("")

        else:  # ERROR
            lines.append(f"## [{idx}] Score: {score} | ⚠️ HATA")
            lines.append("")
            lines.append(f"- Kart A GUID: `{pair.get('kart_a_guid')}`")
            lines.append(f"- Kart B GUID: `{pair.get('kart_b_guid')}`")
            lines.append(f"- Hata: {gerekce}")
            lines.append("")
            lines.append("---")
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"📄 Markdown raporu yazıldı: {output_path}")


def _truncate(text: str, max_len: int = 120) -> str:
    text = text.replace("|", "\\|").replace("\n", " ")
    return text[:max_len] + "…" if len(text) > max_len else text


# ── Temiz TXT (Anki Import) ───────────────────────────────────────────────────
def write_temiz_txt(
    pairs: list[dict],
    card_map: dict,
    output_path: Path,
) -> None:
    """
    Elenmeyen kartların text_raw, baslik, extra alanlarından
    TAB-separated Cloze-MAXXİNG formatında temiz.txt üret.
    """
    # Elenen GUID'leri topla (set ile duplikasyonu önle)
    elenen_guids: set[str] = set()
    for p in pairs:
        if p.get("llm_decision") == "DUPLIKAT" and p.get("elenen_guid"):
            elenen_guids.add(p["elenen_guid"])

    # Deck bilgisini çıkar (ilk kartten al)
    deck_full = "Bilinmiyor"
    if card_map:
        first = next(iter(card_map.values()))
        deck_full = first.get("deck_full", "Bilinmiyor")

    # Tüm kartları filtrele: elenen değil
    korunan_rows: list[tuple[str, str, str]] = []
    for guid, card in card_map.items():
        if guid not in elenen_guids:
            text_raw = card.get("text_raw", "").strip()
            baslik = card.get("baslik", "").strip()
            extra = card.get("extra", "").strip()
            if text_raw:
                korunan_rows.append((text_raw, baslik, extra))

    # Header + satırlar
    header_lines = [
        "#separator:tab",
        "#html:false",
        "#notetype:Cloze-MAXXİNG",
        f"#deck:{deck_full}",
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(header_lines) + "\n")
        for text_raw, baslik, extra in korunan_rows:
            row = f"{text_raw}\t{baslik}"
            if extra:
                row += f"\t{extra}"
            f.write(row + "\n")

    eleme_sayisi = len(elenen_guids)
    korunan_sayisi = len(korunan_rows)
    logger.info(
        f"📋 Temiz TXT yazıldı: {output_path} "
        f"({korunan_sayisi} korunan kart, {eleme_sayisi} GUID elimine edildi)"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="DUS Mentörü Ölüm Maçı — DeepSeek V4 Pro tabanlı kart dedup yargıcı"
    )
    parser.add_argument(
        "--report",
        required=True,
        help="Internal dedup JSON raporu (anki_dedup_local.py çıktısı)",
    )
    parser.add_argument(
        "--original-json",
        dest="original_json",
        default=None,
        help="Tam kart verilerini içeren kaynak JSON ([ders]_[unite].json). "
             "Verilmezse temiz.txt üretilmez.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.84,
        help="Minimum benzerlik eşiği (default: 0.84). Bu değerin altındaki çiftler elenir.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Eş zamanlı API isteği limiti. Reasoning modeller için düşük tut (default: 3)",
    )
    parser.add_argument(
        "--retry-errors",
        action="store_true",
        default=False,
        help="Mevcut {stem}_death_match_results.json'daki ERROR çiftleri yeniden yargıla, "
             "başarılı olanları koru. --original-json ve --threshold önceki çalıştırmadan miras alınır.",
    )
    args = parser.parse_args()

    # ── JSON yükle ────────────────────────────────────────────────────────────
    json_path = Path(args.report)
    if not json_path.exists():
        logger.error(f"Rapor dosyası bulunamadı: {json_path}")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        all_pairs: list[dict] = json.load(f)

    if not all_pairs:
        logger.info("Değerlendirilecek çift yok.")
        return

    out_dir = json_path.parent
    results_json_path = out_dir / f"{json_path.stem}_death_match_results.json"

    # ── --retry-errors: önceki sonuçları yükle, sadece ERROR'ları yeniden yargıla ──
    if args.retry_errors:
        if not results_json_path.exists():
            logger.error(
                f"--retry-errors için önceki sonuç JSON'u bulunamadı: {results_json_path}\n"
                "Önce normal bir çalıştırma yapın."
            )
            return

        with open(results_json_path, "r", encoding="utf-8") as f:
            previous_results: list[dict] = json.load(f)

        # GUID çifti bazlı indeks: (kart_a_guid, kart_b_guid) → önceki sonuç
        prev_index: dict[tuple, dict] = {
            (p["kart_a_guid"], p["kart_b_guid"]): p for p in previous_results
        }

        # Başarılı olanları koru, ERROR olanları yeniden yargılamak üzere işaretle
        to_retry: list[dict] = []
        merged_pairs: list[dict] = []
        for pair in previous_results:
            key = (pair["kart_a_guid"], pair["kart_b_guid"])
            if pair.get("llm_decision") == "ERROR":
                # Orijinal çift verilerini al (kart_a_metin vb.) ve kopyala
                fresh = dict(pair)
                fresh.pop("llm_decision", None)
                fresh.pop("llm_korunan", None)
                fresh.pop("llm_elenen", None)
                fresh.pop("llm_gerekce", None)
                fresh.pop("korunan_guid", None)
                fresh.pop("elenen_guid", None)
                to_retry.append(fresh)
                merged_pairs.append(fresh)  # placeholder — güncellenir
            else:
                merged_pairs.append(pair)

        if not to_retry:
            logger.info("Yeniden denenecek ERROR çift yok. Tüm kararlar zaten başarılı.")
            return

        logger.info(
            f"--retry-errors: {len(previous_results)} önceki sonuç yüklendi. "
            f"{len(to_retry)} ERROR çift yeniden yargılanacak."
        )
        asyncio.run(run_all_judges(to_retry, args.concurrency))

        # Yeniden yargılanan çiftleri merged_pairs'e geri yaz
        retry_index: dict[tuple, dict] = {
            (p["kart_a_guid"], p["kart_b_guid"]): p for p in to_retry
        }
        filtered_pairs = []
        for pair in merged_pairs:
            key = (pair["kart_a_guid"], pair["kart_b_guid"])
            if key in retry_index:
                filtered_pairs.append(retry_index[key])
            else:
                filtered_pairs.append(pair)

        threshold_used = previous_results[0].get("_threshold", args.threshold) if previous_results else args.threshold

    else:
        # ── Normal çalıştırma ─────────────────────────────────────────────────
        # Threshold filtresi
        filtered_pairs = [p for p in all_pairs if p.get("score", 0) >= args.threshold]
        skipped = len(all_pairs) - len(filtered_pairs)
        logger.info(
            f"Toplam {len(all_pairs)} çift | {skipped} çift eşik altında atlandı "
            f"(threshold={args.threshold}) | {len(filtered_pairs)} çift yargıya gönderilecek"
        )

        if not filtered_pairs:
            logger.info("Eşik üzerinde hiç çift yok, işlem durduruluyor.")
            return

        asyncio.run(run_all_judges(filtered_pairs, args.concurrency))
        threshold_used = args.threshold

    # ── Sonuçları JSON'a kaydet (resume/retry için) ──────────────────────────
    results_to_save = []
    for p in filtered_pairs:
        entry = dict(p)
        entry["_threshold"] = threshold_used
        results_to_save.append(entry)

    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(results_to_save, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Sonuçlar JSON'a kaydedildi: {results_json_path}")

    # ── Original JSON haritası ─────────────────────────────────────────────────
    card_map: dict[str, dict] = {}
    original_json_arg = args.original_json if not args.retry_errors else None
    # retry-errors modunda original_json argümanı verilmemişse results JSON'dan ders/ünite al
    if not args.retry_errors and args.original_json:
        orig_path = Path(args.original_json)
        if orig_path.exists():
            with open(orig_path, "r", encoding="utf-8") as f:
                cards: list[dict] = json.load(f)
            card_map = {c["guid"]: c for c in cards if "guid" in c}
            logger.info(f"Original JSON yüklendi: {len(card_map)} kart haritaya alındı.")
        else:
            logger.warning(f"Original JSON bulunamadı: {orig_path} — temiz.txt üretilmeyecek.")
    elif args.retry_errors and args.original_json:
        orig_path = Path(args.original_json)
        if orig_path.exists():
            with open(orig_path, "r", encoding="utf-8") as f:
                cards: list[dict] = json.load(f)
            card_map = {c["guid"]: c for c in cards if "guid" in c}
            logger.info(f"Original JSON yüklendi: {len(card_map)} kart haritaya alındı.")

    # ── Çıktı dosya yolları ───────────────────────────────────────────────────
    # Çıktı 1: Markdown rapor
    md_path = out_dir / f"{json_path.stem}_death_match_raporu.md"
    write_markdown_report(filtered_pairs, json_path, threshold_used, md_path)

    # Çıktı 2: Temiz TXT (original_json varsa)
    if card_map:
        first_card = next(iter(card_map.values()))
        ders = first_card.get("ders", "ders")
        unite = first_card.get("unite", "unite")
        temiz_path = out_dir / f"{ders}_{unite}_temiz.txt"
        write_temiz_txt(filtered_pairs, card_map, temiz_path)
    else:
        logger.warning("Original JSON haritası yok — temiz.txt atlandı.")

    # ── Özet ─────────────────────────────────────────────────────────────────
    duplikat_n = sum(1 for p in filtered_pairs if p.get("llm_decision") == "DUPLIKAT")
    farkli_n = sum(1 for p in filtered_pairs if p.get("llm_decision") == "FARKLI")
    error_n = sum(1 for p in filtered_pairs if p.get("llm_decision") == "ERROR")

    logger.info("=" * 60)
    logger.info(f"⚔️  ÖLÜM MAÇI TAMAMLANDI")
    logger.info(f"   Model    : {MODEL}")
    logger.info(f"   Rapor    : {md_path.name}")
    logger.info(f"   Toplam   : {len(filtered_pairs)} çift")
    logger.info(f"   Duplikat : {duplikat_n}  |  Farklı : {farkli_n}  |  Hata : {error_n}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
