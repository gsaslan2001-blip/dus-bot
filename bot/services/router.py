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
{"intent": "kategori_adi"}

Kullanici mesaji: {message}

Cevap:"""


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
    """Hafif DeepSeek cagrisi ile intent siniflandirmasi."""
    try:
        resp = await deepseek.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": ROUTER_PROMPT.format(message=message)}],
            max_tokens=30,
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        intent = _parse_intent(text)
        log.info(f"[router] intent={intent} msg={message[:80]}")
        return intent
    except Exception as e:
        log.warning(f"[router] siniflandirma hatasi: {e}, varsayilan=genel")
        return "genel"
