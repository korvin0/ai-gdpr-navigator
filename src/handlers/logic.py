"""Обработчики логического квеста GDPR (Фаза 0)."""

import re

from aiogram import F, Router
from aiogram.types import CallbackQuery

from ..formatting import escape_md
from ..keyboards import kb_yes_no_info
from ..sheets_reader import get_logic_node
from ..state import get_state
from .ai_act import start_ai_act_screening

router = Router()


def _parse_gdpr_flag(next_node: str) -> bool | None:
    """Достать gdpr=True/False из составного значения перехода Google Sheets."""
    match = re.search(r"gdpr\s*=\s*(true|false)", next_node, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower() == "true"


def _apply_ai_act_context(state: dict, node_id: str, action: str, next_node: str) -> bool:
    """Выставить флаги при переходе из блока L в блок M."""
    normalized_next = next_node.strip()
    explicit_gdpr = _parse_gdpr_flag(normalized_next)
    goes_to_m1 = bool(re.search(r"\bM1\b", normalized_next, flags=re.IGNORECASE))

    if explicit_gdpr is not None and goes_to_m1:
        state["gdpr_status"] = "mandatory" if explicit_gdpr else "anonymous"
        state["gdpr_mandatory"] = explicit_gdpr
        if node_id == "L3" and action == "no":
            state["attack_risk"] = True
        return True

    if not goes_to_m1:
        return False

    if node_id == "L1" and action == "no":
        state["gdpr_status"] = "anonymous"
        state["gdpr_mandatory"] = False
    elif node_id == "L2" and action == "yes":
        state["gdpr_status"] = "mandatory"
        state["gdpr_mandatory"] = True
    elif node_id == "L3" and action == "no":
        state["gdpr_status"] = "mandatory"
        state["gdpr_mandatory"] = True
        state["attack_risk"] = True
    elif node_id == "L4" and action == "yes":
        state["gdpr_status"] = "anonymous"
        state["gdpr_mandatory"] = False
    elif node_id == "L4" and action == "no":
        state["gdpr_status"] = "mandatory"
        state["gdpr_mandatory"] = True
    else:
        state["gdpr_status"] = "mandatory"
        state["gdpr_mandatory"] = True

    return True


async def send_logic_question_start_callback(callback: CallbackQuery, state: dict) -> None:
    """Отправить первый вопрос логического квеста."""
    node_id = state["logic_node"]
    node = get_logic_node(node_id)

    if not node:
        await callback.message.answer("⚠️ Ошибка: узел не найден. Начните заново с /start")
        return

    state["logic_path"].append(node_id)

    q_num = len(state["logic_path"])
    text = f"🧩 *Проверка применимости GDPR\\. Вопрос {q_num}*\n\n{escape_md(node['question'])}"
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_yes_no_info("lg"))


async def send_logic_question(callback: CallbackQuery, state: dict) -> None:
    """Отправить следующий вопрос логического квеста."""
    node_id = state["logic_node"]
    node = get_logic_node(node_id)

    if not node:
        await callback.message.answer("⚠️ Ошибка: узел не найден. Начните заново с /start")
        return

    state["logic_path"].append(node_id)

    q_num = len(state["logic_path"])
    text = f"🧩 *Проверка применимости GDPR\\. Вопрос {q_num}*\n\n{escape_md(node['question'])}"
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_yes_no_info("lg"))


@router.callback_query(F.data.startswith("lg:"))
async def on_logic_answer(callback: CallbackQuery) -> None:
    """Обработка ответа в логическом квесте."""
    user_id = callback.from_user.id
    state = get_state(user_id)

    action = callback.data.split(":")[1]
    node = get_logic_node(state["logic_node"])

    if not node:
        await callback.answer("Ошибка: узел не найден")
        return

    if action == "info":
        hint = node.get("hint") or "Подсказка недоступна."
        await callback.answer()
        await callback.message.answer(f"ℹ️ *Подсказка:*\n\n{escape_md(hint)}", parse_mode="MarkdownV2")
        return

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    node_id = state["logic_node"]
    next_node = node["next_yes"] if action == "yes" else node["next_no"]

    if _apply_ai_act_context(state, node_id, action, next_node):
        await start_ai_act_screening(callback, state)
    else:
        state["logic_node"] = next_node
        await send_logic_question(callback, state)
