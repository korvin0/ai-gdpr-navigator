"""Обработчики чек-листа мер (Фаза 2)."""

from typing import Optional

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..formatting import escape_md
from ..keyboards import kb_checklist_item, kb_checklist_progress
from ..sheets_reader import filter_content_by_state
from ..state import STATE_CHECKLIST, STATE_REPORT, get_state
from .report import send_report

router = Router()

AI_ACT_TRIGGER_TOKENS = (
    "is_high_risk",
    "is_gen_ai",
    "ai_type",
    "is_creator",
    "is_modifier",
    "is_brand_owner",
    "prohibited_type",
    "is_prohibited",
)


def _find_item_by_id(items: list[dict], item_id: str) -> Optional[dict]:
    """Найти пункт по ID."""
    for item in items:
        if item["id"] == item_id:
            return item
    return None


def _active_scope_suffix(state: dict) -> str:
    """Определить fallback-сферу для сквозных задач без явного trigger_variable."""
    profile = state.get("profile", {})
    has_gdpr = bool(state.get("gdpr_mandatory"))
    has_ai_act = state.get("ai_act_status") == "in_scope" and (
        bool(profile.get("is_high_risk")) or bool(profile.get("is_gen_ai"))
    )

    if has_gdpr and has_ai_act:
        return "GDPR & AI Act"
    if has_ai_act:
        return "AI Act"
    return "GDPR"


def _checklist_scope_suffix(item: dict, state: dict) -> str:
    """Определить регуляторный контекст конкретного пункта чек-листа."""
    if state.get("ai_act_status") == "AIA_OUT_OF_SCOPE" or state.get("AIA_OUT_OF_SCOPE") is True:
        return "GDPR"

    trigger = (item.get("trigger_variable") or "").lower()
    has_gdpr = "gdpr_mandatory" in trigger
    has_ai_act = any(token in trigger for token in AI_ACT_TRIGGER_TOKENS)

    if has_gdpr and has_ai_act:
        return "GDPR & AI Act"
    if has_gdpr:
        return "GDPR"
    if has_ai_act:
        return "AI Act"
    return _active_scope_suffix(state)


@router.callback_query(F.data == "start_checklist")
async def on_start_checklist(callback: CallbackQuery) -> None:
    """Начало чек-листа мер."""
    user_id = callback.from_user.id
    state = get_state(user_id)

    items = filter_content_by_state(state)
    state["content_items"] = items
    state["content_index"] = 0
    state["content_done"] = set()
    state["content_skipped"] = set()
    state["state"] = STATE_CHECKLIST

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    await send_checklist_item(callback, state)


async def send_checklist_item(callback: CallbackQuery, state: dict) -> None:
    """Отправить текущий пункт чек-листа."""
    items = state["content_items"]
    idx = state["content_index"]

    if idx >= len(items):
        state["state"] = STATE_REPORT
        await send_report(callback, state)
        return

    item = items[idx]
    scope_suffix = _checklist_scope_suffix(item, state)

    text = (
        f"📌 *Шаг №{idx + 1} к соответствию {escape_md(scope_suffix)}*\n"
        f"🤹 {escape_md(item['sheet'])}\n\n"
        f"{escape_md(item['requirement'])}"
    )

    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_checklist_item(item["id"]))


@router.callback_query(F.data.startswith("ch:"))
async def on_checklist_action(callback: CallbackQuery) -> None:
    """Обработка действий в чек-листе."""
    user_id = callback.from_user.id
    state = get_state(user_id)

    parts = callback.data.split(":")
    action = parts[1]
    item_id = parts[2] if len(parts) > 2 else ""

    if action == "progress":
        await show_progress(callback, state)
        return

    if action == "continue":
        await callback.answer()
        await send_checklist_item(callback, state)
        return

    if action == "info":
        item = _find_item_by_id(state["content_items"], item_id)
        if item:
            hint = item.get("detailed_hint") or "Подробная информация недоступна."
            await callback.answer()
            await callback.message.answer(f"ℹ️ *Подробнее:*\n\n{escape_md(hint)}", parse_mode="MarkdownV2")
        else:
            await callback.answer("Пункт не найден")
        return

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    if action == "done":
        state["content_done"].add(item_id)
    elif action == "skip":
        state["content_skipped"].add(item_id)

    state["content_index"] += 1
    await send_checklist_item(callback, state)


async def show_progress(callback: CallbackQuery, state: dict) -> None:
    """Показать прогресс чек-листа."""
    total = len(state["content_items"])
    done = len(state["content_done"])
    skipped = len(state["content_skipped"])
    remaining = total - done - skipped

    percent = int((done / total) * 100) if total > 0 else 0

    text = (
        f"📈 *Прогресс проверки*\n\n"
        f"✅ Выполнено: {done}\n"
        f"⏭️ Пропущено: {skipped}\n"
        f"📋 Осталось: {remaining}\n\n"
        f"Общий прогресс: *{percent}%*"
    )

    await callback.answer()
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_checklist_progress())
