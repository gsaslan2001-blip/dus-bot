import json
import logging
from bot.settings import DEEPSEEK_MODEL
from bot.deps import deepseek

log = logging.getLogger(__name__)

ROUTER_PROMPT = """Kullanicinin mesajini su kategorilerden birine siniflandir:
- ders_calis: Konu anlatimi veya ders calisma (ornek: 'SCC patogenezini anlat')
- soru_sor: DUS sorusu cozme (ornek: 'bu soruyu cozer misin?')
- cikmis_analiz: Sinav pattern veya cikmis soru analizi (ornek: 'en cok cikan konular')
- hafiza: Kullanicinin kendi notlari/ilerlemesi (ornek: 'en son ne calismistim?')
- genel: Selamlasma, sohbet (ornek: 'selam')

SADECE su formatta JSON dondur, baska hicbir sey yazma:
{{"intent": "kategori_adi"}}

Kullanici mesaji: {message}

Cevap:"""

# --- Prefix-based routing: /komut mesaj → doğrudan yönlendirme ---
# Format: (prefix_list, intent, forced_index_hint)
# forced_index_hint: orchestrator'a hangi index'in zorunlu olduğunu söyler
PREFIX_ROUTES: list[tuple[list[str], str, str | None]] = [
    (["/mypdf", "/pdfs", "/pdf", "/ders", "/not"], "ders_calis", "myppdfs"),
    (["/brain", "/hafiza", "/memory", "/ilerleme"], "hafiza", "mybrain"),
    (["/soru", "/test", "/quiz", "/coz"], "soru_sor", None),
    (["/anki", "/kart", "/flashcard"], "ders_calis", "anki"),
    (["/cikmis", "/sinav"], "cikmis_analiz", None),
]

# Keyword-based intent detection — fast path, no API call needed
DERS_CALIS_KEYWORDS = [
    "anlat", "açıkla", "detaylı", "konu", "nedir", "nasıl", "patogenez",
    "etyoloji", "sınıflama", "tedavi", "tanı", "teşhis", "bulgu", "klinik",
    "histopatoloji", "radyolojik", "prognoz", "ayırıcı tanı", "mekanizma",
    "fizyopatoloji", "embriyoloji", "histoloji", "anatomi", "fonksiyon",
]

SORU_KEYWORDS = [
    "soru", "çöz", "cevap", "doğru", "yanlış", "hangisi", "aşağıdakilerden",
    "sınav", "test", "hangisidir", "değildir", "aşağıdakiler",
]

HAFIZA_KEYWORDS = [
    "en son", "çalıştım", "ilerleme", "nerede", "kaldım", "notlarım",
    "hafıza", "kaydet", "hatırla", "ne zaman", "kaçıncı",
]

def _prefix_intent(message: str) -> tuple[str, str | None, str] | None:
    """Check for prefix-based routing. Returns (intent, forced_index, cleaned_message) or None."""
    msg_stripped = message.strip()
    for prefixes, intent, forced_index in PREFIX_ROUTES:
        for prefix in prefixes:
            if msg_stripped.lower().startswith(prefix.lower()):
                # Extract the message after the prefix
                remainder = msg_stripped[len(prefix):].strip()
                if not remainder:
                    remainder = msg_stripped  # Keep original if nothing after prefix
                return (intent, forced_index, remainder)
    return None

def _keyword_intent(message: str) -> str | None:
    """Fast keyword-based intent pre-check. Returns None if uncertain (needs LLM)."""
    msg_lower = message.lower().strip()
    # Very short messages → likely chat
    if len(msg_lower) < 10:
        if any(w in msg_lower for w in ["selam", "merhaba", "hey", "sa", "slm", "nasılsın"]):
            return "genel"
        return None  # Too short to decide

    # Check hafiza keywords first (specific patterns)
    if any(kw in msg_lower for kw in HAFIZA_KEYWORDS):
        return "hafiza"

    # Check soru keywords
    if any(kw in msg_lower for kw in SORU_KEYWORDS):
        return "soru_sor"

    # Check ders_calis keywords
    if any(kw in msg_lower for kw in DERS_CALIS_KEYWORDS):
        return "ders_calis"

    return None  # Uncertain, needs LLM


def _parse_intent(text: str) -> str:
    """Robust JSON parsing — handles markdown code blocks, bare strings, extra text."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
        if text.endswith("```"):
            text = text[:-3]
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed.get("intent", "genel")
        elif isinstance(parsed, str):
            return parsed if parsed in ("ders_calis", "soru_sor", "cikmis_analiz", "hafiza", "genel") else "genel"
    except json.JSONDecodeError:
        pass
    # Try to find a JSON object in the text
    import re
    match = re.search(r'\{[^}]+\}', text)
    if match:
        try:
            return json.loads(match.group()).get("intent", "genel")
        except (json.JSONDecodeError, AttributeError):
            pass
    return "genel"


async def classify_intent(message: str) -> str:
    """Prefix-based → Keyword-based → DeepSeek fallback intent classification."""
    # Fast path 1: Prefix-based routing (e.g., "/mypdf SCC patogenezi")
    # Note: returns cleaned message via side-channel for handler to use
    prefix_result = _prefix_intent(message)
    if prefix_result is not None:
        intent, forced_index, cleaned_msg = prefix_result
        log.info(f"[router] prefix intent={intent} forced_index={forced_index} msg={cleaned_msg[:80]}")
        return intent

    # Fast path 2: Keyword-based detection (saves API call)
    kw_intent = _keyword_intent(message)
    if kw_intent is not None:
        log.info(f"[router] keyword intent={kw_intent} msg={message[:80]}")
        return kw_intent

    # Slow path: DeepSeek API call
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
    """Extract prefix routing info without classifying. Returns (forced_index, cleaned_message)."""
    result = _prefix_intent(message)
    if result is not None:
        return result[1], result[2]
    return None, message
