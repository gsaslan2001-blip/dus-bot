import json
import logging
from bot.settings import DEEPSEEK_MODEL
from bot.deps import deepseek

log = logging.getLogger(__name__)


VALID_INTENTS = ("ders_calis", "soru_sor", "genel")

ROUTER_PROMPT = """Kullanicinin mesajini su kategorilerden birine siniflandir:
- ders_calis: Konu anlatimi veya ders calisma (ornek: 'SCC patogenezini anlat')
- soru_sor: DUS sorusu cozme (ornek: 'bu soruyu cozer misin?')
- genel: Selamlasma, sohbet (ornek: 'selam')

SADECE su formatta JSON dondur, baska hicbir sey yazma:
{{"intent": "kategori_adi"}}

Kullanici mesaji: {message}

Cevap:"""

# Prefix → (intent, forced_index)
# forced_index: hangi Pinecone index'ine OZEL gidecegi — orchestrator bu prefix varsa SADECE o index'i arar
PREFIX_ROUTES: list[tuple[list[str], str, str | None]] = [
    (["/mypdf", "/pdfs", "/pdf", "/ders", "/not"], "ders_calis", "myppdfs"),
    (["/soru", "/test", "/quiz", "/coz"], "soru_sor", "dusbankasi"),
]

# Kullanıcı prefix'i tek başına gönderince gösterilecek yardım mesajları
PREFIX_HELP: dict[str | None, str] = {
    "myppdfs": (
        "Ders notlari modu aktif.\n\n"
        "Ne aramak istiyorsun?\n"
        "Ornek: SCC patogenezi, periodontit tedavisi, amiloblastom"
    ),
    "dusbankasi": (
        "Soru bankasi modu aktif. (~20.000 DUS sorusu)\n\n"
        "Hangi konuda soru cozmek istiyorsun?\n"
        "Ornek: patoloji sorularina bakalim, amiloblastom sorusu, radyoloji MCQ"
    ),
}


def get_prefix_help(forced_index: str | None) -> str:
    return PREFIX_HELP.get(forced_index, "Mod aktif. Ne aramak istiyorsun?")


# Keyword-based intent detection — fast path, no API call needed
DERS_CALIS_KEYWORDS = [
    "anlat", "açıkla", "acikla", "detaylı", "detayli", "konu", "nedir", "nasıl", "nasil",
    "patogenez", "etyoloji", "sınıflama", "sinifla", "sınıflandır", "siniflandir",
    "tedavi", "tanı", "tani", "teşhis", "teshis", "bulgu", "klinik",
    "histopatoloji", "radyolojik", "prognoz", "mekanizma", "fizyopatoloji",
    "embriyoloji", "histoloji", "anatomi", "fonksiyon", "ayırıcı tanı", "ayirici",
    "immun", "immün", "yetmezlik", "sendrom", "hastalık", "hastalik",
    "enfeksiyon", "inflamasyon", "tümör", "tumor", "kist", "apse",
    "kanser", "karsinom", "lösemi", "losemi", "lenfoma", "fibrozis",
    "nekroz", "atrofi", "hipertrofi", "displazi", "metaplazi",
    "ülser", "ulser", "abse", "granülom", "granulom",
    "tip 1", "tip 2", "tip 3", "tip 4", "tip i", "tip ii", "tip iii",
    "evre", "derece", "grade", "stage", "sınıf", "sinif", "alt tip", "varyant",
    "ankraj", "maloklüzyon", "malokluzyon", "sefalometri", "braket", "headgear",
    "pekiştirme", "retansiyon", "sınıf 2", "sınıf 3", "angle", "sürme",
    "ortodontik", "apareyy", "aktivatör",
    "patoloji", "radyoloji", "endodonti", "protez", "histoloji",
    "fizyoloji", "periodontoloji", "cerrahi", "farmakoloji",
    "pedodonti", "restoratif", "biyokimya", "mikrobiyoloji", "ortodonti",
    "ameloblastom", "keratokist", "granülom", "periapkal", "pulpit",
    "gingivit", "periodontit", "osteomiyelit", "osteosarkom",
    "amelogenez", "dentinogenez", "ossifikasyon",
]

SORU_KEYWORDS = [
    "soru", "çöz", "cevap", "doğru", "yanlış", "hangisi", "aşağıdakilerden",
    "sınav", "test", "hangisidir", "değildir", "aşağıdakiler",
]

def _prefix_intent(message: str) -> tuple[str, str | None, str, bool] | None:
    """Prefix tabanlı yönlendirme. (intent, forced_index, cleaned_text, is_prefix_only) döner.

    is_prefix_only=True: kullanıcı sadece prefix yazdı, sorgu yok — yardım mesajı göster.
    """
    msg_stripped = message.strip()
    for prefixes, intent, forced_index in PREFIX_ROUTES:
        for prefix in prefixes:
            if msg_stripped.lower().startswith(prefix.lower()):
                remainder = msg_stripped[len(prefix):].strip()
                is_prefix_only = len(remainder) == 0
                return (intent, forced_index, remainder, is_prefix_only)
    return None


def _keyword_intent(message: str) -> str | None:
    """Keyword tabanlı hızlı intent tespiti. None döndürürse LLM kullanılır."""
    msg_lower = message.lower().strip()
    if len(msg_lower) < 10:
        if any(w in msg_lower for w in ["selam", "merhaba", "hey", "sa", "slm", "nasılsın"]):
            return "genel"
        return None

    if any(kw in msg_lower for kw in SORU_KEYWORDS):
        return "soru_sor"

    if any(kw in msg_lower for kw in DERS_CALIS_KEYWORDS):
        return "ders_calis"

    return None


def _parse_intent(text: str) -> str:
    """Robust JSON parsing — markdown code block, bare string ve ekstra metin destekler."""
    if not isinstance(text, str):
        return "genel"
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if "```" in text:
            text = text.split("```")[0]
    text = text.strip()

    def validate(val):
        return val if val in VALID_INTENTS else "genel"

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return validate(parsed.get("intent", "genel"))
        elif isinstance(parsed, str):
            return validate(parsed)
    except Exception:
        pass

    import re
    try:
        match = re.search(r'\{[^}]+\}', text)
        if match:
            parsed = json.loads(match.group())
            if isinstance(parsed, dict):
                return validate(parsed.get("intent", "genel"))
    except Exception:
        pass

    return "genel"


def route_message(message: str) -> tuple[str | None, str | None, str, bool]:
    """Tek geçişte tam yönlendirme. messages.py'nin kullandığı ana API.

    Returns:
        (intent_override, forced_index, cleaned_text, is_prefix_only)

        intent_override=None: keyword/LLM sınıflandırması gerekiyor
        is_prefix_only=True: yardım mesajı gönder, arama yapma
    """
    result = _prefix_intent(message)
    if result is not None:
        intent, forced_index, cleaned, is_only = result
        return intent, forced_index, cleaned, is_only
    return None, None, message, False


async def classify_intent(message: str) -> str:
    """Prefix → Keyword → DeepSeek sıralamasıyla intent sınıflandırması.

    Not: route_message() prefix tespiti dahil her şeyi yapıyor.
    Bu fonksiyon sadece keyword/LLM yolu için çağrılmalı (prefix yoksa).
    """
    prefix_result = _prefix_intent(message)
    if prefix_result is not None:
        intent, forced_index, cleaned_msg, _ = prefix_result
        log.info(f"[router] prefix intent={intent} forced_index={forced_index} msg={cleaned_msg[:80]}")
        return intent

    kw_intent = _keyword_intent(message)
    if kw_intent is not None:
        log.info(f"[router] keyword intent={kw_intent} msg={message[:80]}")
        return kw_intent

    try:
        resp = await deepseek.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": ROUTER_PROMPT.format(message=message)}],
            max_tokens=30,
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        intent = _parse_intent(text)
        log.info(f"[router] deepseek intent={intent} msg={message[:80]}")
        return intent
    except Exception as e:
        log.warning(f"[router] siniflandirma hatasi: {e}, varsayilan=genel")
        return "genel"


def get_prefix_routing(message: str) -> tuple[str | None, str]:
    """Backwards-compat API. (forced_index, cleaned_message) döner.

    Prefix-only mesajlarda cleaned_message="" döner (artık prefix metnini döndürmez).
    Yeni kod için route_message() kullanın.
    """
    result = _prefix_intent(message)
    if result is not None:
        return result[1], result[2]  # forced_index, cleaned_text (prefix-only'de "")
    return None, message
