import logging
from bot.services.router import route_message, get_prefix_help, classify_intent
from bot.services.orchestrator import orchestrate_search
from bot.services.agent_loop import run_agent

log = logging.getLogger(__name__)


async def handle_message(chat_id: int, text: str, send, send_action, context: dict,
                         get_settings, search_cache, get_search_cache_key,
                         send_placeholder=None, edit_message=None) -> None:
    """Ana mesaj işleyici: route → search → agent → respond."""

    # Step 0: Tek geçişte yönlendirme
    intent_override, forced_index, cleaned_text, is_prefix_only = route_message(text)

    # Prefix tek başına gönderildi → arama yapma, yardım mesajı göster ve aktif mod olarak kaydet
    if is_prefix_only:
        context["active_intent"] = intent_override
        context["active_index"] = forced_index
        await send(chat_id, get_prefix_help(forced_index), parse_mode="")
        return

    # Eğer prefix verilmemişse ama aktif bir mod varsa onu kullan
    if not intent_override and "active_intent" in context:
        intent_override = context["active_intent"]
        forced_index = context["active_index"]

    # Step 1: Intent — prefix belirlediyse DeepSeek çağrısını atla
    if intent_override:
        intent = intent_override
        log.info(f"[handler] prefix route: intent={intent} forced={forced_index} msg={cleaned_text[:80]}")
    else:
        intent = await classify_intent(cleaned_text)
        log.info(f"[handler] classified: intent={intent} msg={cleaned_text[:80]}")

    settings = get_settings(chat_id)

    # Step 2: Placeholder gönder (kullanıcı hemen bir şey görür)
    placeholder_msg_id = None
    if send_placeholder:
        placeholder_msg_id = await send_placeholder(chat_id)
    else:
        await send_action(chat_id, "typing")

    # Step 3: Cache kontrolü
    cache_key = get_search_cache_key(cleaned_text, intent, forced_index, settings)
    cached = search_cache.get(cache_key)
    if cached:
        log.info(f"[handler] cache hit: {cache_key[:80]}")
        search_results = cached
    else:
        search_results = await orchestrate_search(
            cleaned_text, intent,
            forced_index=forced_index,
            settings=settings,
        )
        search_cache[cache_key] = search_results

    # Step 4: Response generation
    prior_history = context.get("history", [])
    reasoning_content = None

    # /soru intent: Format Pinecone questions directly (no agent synthesis)
    if intent == "soru_sor":
        questions = search_results.get("questions", [])
        if not questions:
            response = "Soru bankasinda bu sorgu icin uygun soru bulunamadi. Farkli anahtar kelimelerle deneyin."
        else:
            lines = [f"'{cleaned_text}' ile ilgili sorular:\n"]
            seen_questions = set()
            count = 0
            for q in questions:
                q_text = q.get("question", "").strip()
                if not q_text or q_text in seen_questions:
                    continue
                seen_questions.add(q_text)
                count += 1

                lines.append(f"SORU {count}:")
                lines.append(f"{q_text}\n")

                options_str = ""
                for opt in ["a", "b", "c", "d", "e"]:
                    val = q.get(f"option_{opt}", "").strip()
                    if val:
                        options_str += f"{opt.upper()}) {val}\n"
                if options_str:
                    lines.append(options_str)

                lines.append(f"Cevap: {q.get('correct_answer', 'Belirtilmemis')}")
                if q.get("explanation"):
                    lines.append(f"Aciklama: {q.get('explanation')}")
                lines.append("-" * 15 + "\n")

                if count >= 5:
                    break

            response = "\n".join(lines)
    else:
        # Agent synthesis — returns {"content": str, "reasoning_content": str|None}
        agent_result = await run_agent(
            cleaned_text, search_results, settings=settings,
            history=prior_history, intent=intent,
            forced_index=forced_index,
        )
        response = agent_result["content"]
        reasoning_content = agent_result.get("reasoning_content")

    # Step 5: Konuşma geçmişini güncelle — reasoning_content'i sakla
    history = context.get("history", [])
    history.append({"role": "user", "content": cleaned_text})
    assistant_turn = {"role": "assistant", "content": response}
    if reasoning_content:
        assistant_turn["reasoning_content"] = reasoning_content
    history.append(assistant_turn)
    context["history"] = history[-20:]

    # Step 6: Yanıtı gönder — uzun yanıtı satır sınırında parçala (token ortadan bölünmesin),
    # ilk parçayı placeholder'a yaz, kalanını ayrı mesajlarla gönder (yetim "..." kalmasın)
    MAX_PART = 4000

    def _split_parts(t: str) -> list[str]:
        out, s = [], 0
        while s < len(t):
            e = s + MAX_PART
            if e < len(t):
                nl = t.rfind("\n", s, e)
                if nl != -1 and nl > s + MAX_PART // 2:
                    e = nl
            out.append(t[s:e])
            s = e
        return out or [t]

    if placeholder_msg_id and edit_message:
        parts = _split_parts(response)
        ok = await edit_message(chat_id, placeholder_msg_id, parts[0])
        if not ok:
            await send(chat_id, response, parse_mode="")
        else:
            for part in parts[1:]:
                await send(chat_id, part, parse_mode="")
    else:
        await send(chat_id, response, parse_mode="")
