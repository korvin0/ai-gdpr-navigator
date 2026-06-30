"""Обработчики профилирования (триггеры, Фаза 1)."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..analytics import log_event
from ..formatting import escape_md, progress_block
from ..keyboards import kb_start_checklist, kb_yes_no, kb_yes_no_info_trigger
from ..sheets_reader import filter_content_by_state, load_system_triggers
from ..state import STATE_BLOCKED, STATE_TRIGGERS, get_state

router = Router()


def _has_ai_act_measures(state: dict) -> bool:
    """Проверить, есть ли активные AI Act триггеры для текста summary."""
    profile = state.get("profile", {})
    return state.get("ai_act_status") == "in_scope" and (
        bool(profile.get("is_high_risk")) or bool(profile.get("is_gen_ai"))
    )


def _summary_measure_text(state: dict, total: int) -> tuple[str, str, str]:
    """Собрать динамический текст перед запуском чек-листа."""
    gdpr_mandatory = bool(state.get("gdpr_mandatory"))
    has_ai_act = _has_ai_act_measures(state)

    if gdpr_mandatory and has_ai_act:
        return (
            "На основе профиля вашего проекта бот составил список мер для соответствия GDPR и AI Act\\.",
            f"Чтобы полностью соответствовать регуляторным требованиям, нужно выполнить *{total}* мер\\.",
            "Давайте проверим, насколько вы готовы к аудиту\\!",
        )

    if gdpr_mandatory:
        return (
            "На основе профиля вашего проекта бот составил список мер для соответствия GDPR\\.",
            f"Чтобы полностью соответствовать требованиям приватности, нужно выполнить *{total}* мер\\.",
            "Давайте проверим, насколько вы готовы к GDPR\\!",
        )

    if has_ai_act:
        return (
            "На основе профиля вашего проекта бот составил список мер для соответствия AI Act\\.",
            f"Чтобы полностью соответствовать регуляторным требованиям, нужно выполнить *{total}* мер\\.",
            "Давайте проверим, насколько вы готовы к аудиту\\!",
        )

    return (
        "На основе профиля вашего проекта бот составил список применимых мер\\.",
        f"Нужно выполнить *{total}* мер\\.",
        "Давайте проверим, насколько вы готовы к аудиту\\!",
    )


@router.callback_query(F.data == "start_triggers")
async def on_start_triggers(callback: CallbackQuery) -> None:
    """Начало опроса триггеров."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    if state.get("ai_act_status") != "in_scope":
        await callback.answer("Сначала ответьте на вопросы AI Act.", show_alert=True)
        return

    state["state"] = STATE_TRIGGERS
    state["trigger_index"] = 0
    log_event(callback.from_user, phase="phase_1", event="phase_1_started", state=state)

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    await send_trigger_question(callback, state)


async def send_trigger_question(message_or_callback, state: dict) -> None:
    """Отправить следующий вопрос триггера."""
    triggers = load_system_triggers()
    idx = state["trigger_index"]

    if idx >= len(triggers):
        await send_profile_summary(message_or_callback, state)
        return

    trigger = triggers[idx]
    text = f"❓ *Определяем профиль проекта\\. Вопрос {idx + 1}\\.*\n\n{escape_md(trigger['question_text'])}"

    if trigger.get("hint"):
        kb = kb_yes_no_info_trigger("trg", trigger["variable"])
    else:
        kb = kb_yes_no("trg", trigger["variable"])

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, parse_mode="MarkdownV2", reply_markup=kb)
    else:
        await message_or_callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb)


async def send_profile_summary(message_or_callback, state: dict) -> None:
    """Показать резюме профиля после триггеров."""
    profile = state["profile"]

    lines = ["⚙️ *Профиль вашего проекта готов\\!*\n"]

    if profile.get("is_creator"):
        lines.append("• 🔧 Роль: Разработчик модели \\(Model Developer\\)")
    if profile.get("is_brand_owner"):
        lines.append("• 🔧 Роль: Оператор AI\\-системы \\(AI System Operator\\)/Владелец продукта")
    if profile.get("is_modifier"):
        lines.append("• 🔧 Роль: Лицо, модифицирующее модель")

    if profile.get("is_gen_ai"):
        lines.append("• 🤖 Тип: Генеративный ИИ")
    if profile.get("is_child"):
        lines.append("• 👶 Аудитория: Дети/подростки")
    if profile.get("has_scraping"):
        lines.append("• 🌐 Источник: Веб\\-скрейпинг")
    if profile.get("is_high_risk"):
        lines.append("• 🚩 Уровень: Высокий риск")

    if len(lines) == 1:
        lines.append("• Стандартный профиль")

    items = filter_content_by_state(state)
    total = len(items)

    lines.append(f"\n{progress_block(2)}\n")
    measure_intro, measure_total, cta = _summary_measure_text(state, total)
    lines.append(f"{measure_intro}\n")
    lines.append(measure_total)
    lines.append("Пройдите по каждому пункту, отмечая выполненные меры\\.\n")
    lines.append(cta)

    text = "\n".join(lines)

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, parse_mode="MarkdownV2", reply_markup=kb_start_checklist())
    else:
        await message_or_callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_start_checklist())


def _format_prohibited_warning(prohibited_items: list[str]) -> str:
    """Сформировать терминальное предупреждение для prohibited AI."""
    reason = " / ".join(item for item in prohibited_items if item) or "prohibited_type"

    return "\n\n".join([
        "🛑 *КРИТИЧЕСКИЙ СТАТУС: ЗАПРЕЩЕНО В ЕС \\(PROHIBITED AI\\)*",
        escape_md(
            "Ваш продукт использует практики, которые полностью запрещены ст. 5 AI Act. "
            "Вывод этой системы на рынок Европы или её использование может повлечь за собой "
            "немедленный бан продукта и оборотные штрафы до 35 000 000 € "
            "(или 7% от мирового годового оборота компании)."
        ),
        f"*Причина блокировки:* {escape_md('Ваш ИИ использует функции: ' + reason + '.')}",
        (
            "*⚙Что делать дальше?*\n"
            + escape_md(
                "Комплаенс-отчет заблокирован, так как эти функции невозможно «настроить» легально. "
                "Вам необходимо:\n"
                "1. Удалить/вырезать запрещенный функционал из архитектуры системы.\n"
                "2. Ввести геоблокировку (Geo-fencing), если вы хотите оставить эти функции для рынков "
                "США или Азии, полностью закрыв доступ для пользователей и IP-адресов из Европейского союза.\n"
                "После изменения бизнес-логики вы можете пройти тест заново."
            )
        ),
    ])


async def send_prohibited_warning(callback: CallbackQuery, state: dict, trigger: dict) -> None:
    """Остановить сценарий и отправить предупреждение о запрещенном AI."""
    items = trigger.get("options") or state.get("prohibited_items") or []
    state["prohibited_items"] = items
    state["state"] = STATE_BLOCKED
    state["ai_act_status"] = "PROHIBITED_RISK"
    state["global_status"] = "PROHIBITED_RISK"
    log_event(callback.from_user, phase="terminal", event="blocked_prohibited_ai", state=state)

    await callback.message.answer(_format_prohibited_warning(items), parse_mode="MarkdownV2")


@router.callback_query(F.data.startswith("trg:"))
async def on_trigger_answer(callback: CallbackQuery) -> None:
    """Обработка ответа на триггер."""
    user_id = callback.from_user.id
    state = get_state(user_id)

    parts = callback.data.split(":")
    answer = parts[1]
    variable = parts[2] if len(parts) > 2 else ""

    if answer == "info":
        triggers = load_system_triggers()
        idx = state["trigger_index"]
        hint = "Подсказка недоступна."
        if idx < len(triggers):
            hint = triggers[idx].get("hint") or hint
        await callback.answer()
        await callback.message.answer(f"ℹ️ *Подсказка:*\n\n{escape_md(hint)}", parse_mode="MarkdownV2")
        return

    triggers = load_system_triggers()
    idx = state["trigger_index"]
    trigger = triggers[idx] if idx < len(triggers) else {}

    if variable:
        state["profile"][variable] = (answer == "yes")
        if variable == "prohibited_type" and answer == "yes":
            state["profile"]["is_prohibited"] = True
            state["prohibited_items"] = trigger.get("options") or []

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    if variable == "prohibited_type" and answer == "yes":
        await send_prohibited_warning(callback, state, trigger)
        return

    state["trigger_index"] += 1

    await send_trigger_question(callback, state)
