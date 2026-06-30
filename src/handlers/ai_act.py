"""Обработчики скрининга AI Act (Блок M)."""

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..analytics import log_event
from ..formatting import escape_md, progress_block
from ..keyboards import kb_ai_act_scope, kb_ai_target, kb_audit_not_required
from ..sheets_reader import filter_content_by_state, get_logic_node
from ..state import STATE_AI_ACT, STATE_CHECKLIST, STATE_REPORT, STATE_TRIGGERS, get_state
from .checklist import send_checklist_item
from .triggers import send_trigger_question

router = Router()

ANON_DOCUMENTATION_DISCLAIMER = (
    "Документация должна позволять регуляторам и пользователям убедиться, "
    "что модель не обрабатывает персональные данные."
)


async def start_ai_act_screening(callback: CallbackQuery, state: dict) -> None:
    """Запустить блок M после квалификации GDPR."""
    state["state"] = STATE_AI_ACT
    state["ai_act_node"] = "M1"

    if state.get("gdpr_mandatory") is False:
        text = (
            "🏆 *GDPR: обязательный трек не выявлен*\n\n"
            "Ваша модель квалифицирована как не обрабатывающая персональные данные\\.\n\n"
            f"📋 *Важно:* {escape_md(ANON_DOCUMENTATION_DISCLAIMER)}\n\n"
            "Теперь проверим применимость AI Act\\."
        )
    else:
        text = (
            "⚖️ *GDPR применим*\n\n"
            "Ваша модель признана носителем персональных данных\\.\n\n"
            f"{progress_block(1)}\n\n"
            "Теперь проверим применимость AI Act\\."
        )

    if state.get("attack_risk"):
        text += (
            "\n\n⚠️ *Риск извлечения данных:* без тестов на извлечение ПД "
            "анонимность модели не считается подтверждённой\\."
        )

    await callback.message.answer(text, parse_mode="MarkdownV2")
    await send_ai_act_question(callback, state)


async def send_ai_act_question(callback: CallbackQuery, state: dict) -> None:
    """Отправить текущий вопрос блока M."""
    node_id = state.get("ai_act_node", "M1")
    node = get_logic_node(node_id)

    if not node or not node.get("question"):
        await callback.message.answer(
            f"⚠️ Ошибка: вопрос {escape_md(node_id)} не найден в Logic\\_GDPR\\. "
            "Проверьте строки M1/M2 в Google Sheets\\.",
            parse_mode="MarkdownV2",
        )
        return

    if node_id == "M1":
        text = f"🇪🇺 *Скрининг AI Act\\. Вопрос 1*\n\n{escape_md(node['question'])}"
        await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_ai_target())
        return

    text = f"🇪🇺 *Скрининг AI Act\\. Вопрос 2*\n\n{escape_md(node['question'])}"
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_ai_act_scope())


@router.callback_query(F.data.startswith("ai_act:"))
async def on_ai_act_answer(callback: CallbackQuery) -> None:
    """Обработка ответов M1/M2."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    answer = callback.data.split(":")[1]
    node_id = state.get("ai_act_node", "M1")

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    if node_id == "M1":
        if answer in {"yes", "no"}:
            answer = "system" if answer == "yes" else "model"
        if answer not in {"model", "system"}:
            await callback.message.answer("⚠️ Неизвестный тип объекта проверки. Начните заново с /start")
            return

        state["ai_type"] = answer
        state["target"] = answer
        state["ai_act_node"] = "M2"
        await send_ai_act_question(callback, state)
        return

    if answer == "yes":
        state["ai_act_status"] = "in_scope"
        state["state"] = STATE_TRIGGERS
        state["trigger_index"] = 0
        log_event(callback.from_user, phase="phase_1", event="phase_1_started", state=state)
        await send_trigger_question(callback, state)
        return

    state["ai_act_status"] = "AIA_OUT_OF_SCOPE"

    if state.get("gdpr_mandatory") is False:
        state["state"] = STATE_REPORT
        state["content_items"] = []
        state["content_index"] = 0
        state["content_done"] = set()
        state["content_skipped"] = set()
        log_event(callback.from_user, phase="terminal", event="audit_not_required", state=state)

        await callback.message.answer(
            "ℹ️ Ваш продукт не связан с рынком Европейского союза, поэтому специфические требования "
            "по AI Act на него не распространяются\\.\n\n"
            "Также обязательный трек GDPR не выявлен, поэтому чек\\-лист мер не требуется\\.\n\n"
            f"📋 {escape_md(ANON_DOCUMENTATION_DISCLAIMER)}",
            parse_mode="MarkdownV2",
            reply_markup=kb_audit_not_required(),
        )
        return

    state["state"] = STATE_CHECKLIST
    state["content_items"] = filter_content_by_state(state)
    state["content_index"] = 0
    state["content_done"] = set()
    state["content_skipped"] = set()
    log_event(callback.from_user, phase="phase_2", event="phase_2_started", state=state)

    await callback.message.answer(
        "ℹ️ Ваш продукт не связан с рынком Европейского союза, поэтому специфические требования "
        "по AI Act на него не распространяются\\. Опрос по AI Act остановлен, перехожу к списку применимых мер\\.",
        parse_mode="MarkdownV2",
    )
    await send_checklist_item(callback, state)
