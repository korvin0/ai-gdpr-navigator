"""Inline-клавиатуры бота."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_yes_no(callback_prefix: str, variable: str = "") -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет."""
    suffix = f":{variable}" if variable else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"{callback_prefix}:yes{suffix}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{callback_prefix}:no{suffix}"),
        ]
    ])


def kb_yes_no_info_trigger(callback_prefix: str, variable: str = "") -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет/Инфо для триггеров."""
    suffix = f":{variable}" if variable else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"{callback_prefix}:yes{suffix}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{callback_prefix}:no{suffix}"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ Инфо", callback_data=f"{callback_prefix}:info{suffix}"),
        ]
    ])


def kb_yes_no_info(callback_prefix: str) -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет/Инфо для логического квеста."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"{callback_prefix}:yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{callback_prefix}:no"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ Что это значит?", callback_data=f"{callback_prefix}:info"),
        ]
    ])


def kb_ai_target() -> InlineKeyboardMarkup:
    """Клавиатура выбора объекта AI Act-скрининга."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏗️ Система", callback_data="ai_act:yes"),
            InlineKeyboardButton(text="🧠 Модель", callback_data="ai_act:no"),
        ]
    ])


def kb_ai_act_scope() -> InlineKeyboardMarkup:
    """Клавиатура географического охвата AI Act."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="ai_act:yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="ai_act:no"),
        ]
    ])


def kb_checklist_item(item_id: str) -> InlineKeyboardMarkup:
    """Клавиатура для пункта чек-листа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Сделано", callback_data=f"ch:done:{item_id}"),
            InlineKeyboardButton(text="ℹ️ Подробнее", callback_data=f"ch:info:{item_id}"),
        ],
        [
            InlineKeyboardButton(text="❌ Нет, не сделано", callback_data=f"ch:skip:{item_id}"),
        ]
    ])


def kb_checklist_progress() -> InlineKeyboardMarkup:
    """Клавиатура прогресса чек-листа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📈 Посмотреть прогресс", callback_data="ch:progress")],
        [InlineKeyboardButton(text="➡️ Продолжить", callback_data="ch:continue")],
    ])


def kb_report() -> InlineKeyboardMarkup:
    """Клавиатура финального отчета."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Оставить отзыв", callback_data="report:review")],
        [InlineKeyboardButton(text="🔄 Начать новый аудит", callback_data="report:restart")],
    ])


def kb_start_triggers() -> InlineKeyboardMarkup:
    """Кнопка начала опроса триггеров."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Определить профиля проекта", callback_data="start_triggers")]
    ])


def kb_start_checklist() -> InlineKeyboardMarkup:
    """Кнопка начала чек-листа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Перейти к списку мер", callback_data="start_checklist")]
    ])


def kb_warn_continue() -> InlineKeyboardMarkup:
    """Кнопка продолжения после предупреждения."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Понятно, идем дальше", callback_data="warn_continue")]
    ])


def kb_audit_not_required() -> InlineKeyboardMarkup:
    """Кнопка после завершения без аудита."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Начать новый аудит", callback_data="report:restart")],
    ])


def kb_gdpr_knowledge() -> InlineKeyboardMarkup:
    """Клавиатура: знаете ли вы, применяется ли GDPR?"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤔 Я НЕ ЗНАЮ", callback_data="gdpr_know:unknown")],
        [InlineKeyboardButton(text="✅ Я точно знаю, что ПРИМЕНЯЕТСЯ", callback_data="gdpr_know:yes")],
        [InlineKeyboardButton(text="❌ Я точно знаю, что НЕ ПРИМЕНЯЕТСЯ", callback_data="gdpr_know:no")],
    ])
