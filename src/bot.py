"""
AI GDPR Navigator - FSM-бот с 4 фазами:
- Фаза 0: Логический квест GDPR (определение применимости)
- Фаза 1: Профилирование (триггеры)
- Фаза 2: Интерактивный чек-лист мер
- Фаза 3: Финальный отчет
"""
import os
import logging
from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove

from .sheets_reader import (
    load_system_triggers,
    load_logic_gdpr,
    get_logic_node,
    load_content_checklist,
    filter_content_by_profile,
    load_gemini_kb,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === FSM States ===
STATE_LOGIC = 0      # Фаза 0: Логический квест GDPR
STATE_TRIGGERS = 1   # Фаза 1: Профилирование (триггеры)
STATE_CHECKLIST = 2  # Фаза 2: Чек-лист мер
STATE_REPORT = 3     # Фаза 3: Отчет

# === User State Storage (in-memory, anonymous) ===
USER_STATE: dict[int, dict] = {}


def get_state(user_id: int) -> dict:
    """Получить или создать состояние пользователя."""
    if user_id not in USER_STATE:
        USER_STATE[user_id] = _create_initial_state()
    return USER_STATE[user_id]


def _create_initial_state() -> dict:
    """Создать начальное состояние."""
    return {
        "state": STATE_LOGIC,
        "profile": {
            # Старые триггеры (из Content_Checklist)
            "is_gen_ai": False,
            "is_child": False,
            "has_scraping": False,
            "is_high_risk": False,
            # Новые триггеры (роли)
            "is_creator": False,
            "is_brand_owner": False,
            "is_modifier": False,
        },
        "gdpr_status": None,  # "anonymous" | "mandatory"
        "trigger_index": 0,
        "logic_node": "L1",
        "logic_path": [],
        "content_items": [],
        "content_index": 0,
        "content_done": set(),
        "content_skipped": set(),
    }


def reset_state(user_id: int) -> dict:
    """Сбросить состояние пользователя."""
    USER_STATE[user_id] = _create_initial_state()
    return USER_STATE[user_id]


# === Keyboard Builders ===
def kb_yes_no(callback_prefix: str, variable: str = "") -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет."""
    suffix = f":{variable}" if variable else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data=f"{callback_prefix}:yes{suffix}"),
            InlineKeyboardButton(text="❌ Нет", callback_data=f"{callback_prefix}:no{suffix}"),
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
        [InlineKeyboardButton(text="💬 Спросить Gemini AI", callback_data="report:gemini")],
        [InlineKeyboardButton(text="🔄 Начать новый аудит", callback_data="report:restart")],
    ])


def kb_start_triggers() -> InlineKeyboardMarkup:
    """Кнопка начала опроса триггеров."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Продолжить профилирование", callback_data="start_triggers")]
    ])


def kb_start_checklist() -> InlineKeyboardMarkup:
    """Кнопка начала чек-листа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Перейти к чек-листу мер", callback_data="start_checklist")]
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
        [InlineKeyboardButton(text="🤔 Я точно не знаю", callback_data="gdpr_know:unknown")],
        [InlineKeyboardButton(text="✅ Точно знаю, что применяется", callback_data="gdpr_know:yes")],
        [InlineKeyboardButton(text="❌ Точно знаю, что НЕ применяется", callback_data="gdpr_know:no")],
    ])


# === Router ===
router = Router()


# === Start: Предварительный вопрос о знании GDPR ===
@router.message(Command("start"))
@router.message(Command("cancel"))
async def cmd_start(message: Message) -> None:
    """Начало или перезапуск бота."""
    user_id = message.from_user.id if message.from_user else 0
    reset_state(user_id)
    
    await message.answer(
        "👋 *Добро пожаловать в AI GDPR Navigator\\!*\n\n"
        "Результаты работы бота носят справочный характер и основаны на информации, предоставленной пользователем\\. Окончательная правовая квалификация требует отдельного анализа экспертами\\.\n\n"
        "Я помогу проверить ваш ИИ\\-проект на соответствие нормам GDPR\\.\n\n"
        "Знаете ли вы, применяется ли GDPR к вашей модели?",
        parse_mode="MarkdownV2",
        reply_markup=kb_gdpr_knowledge(),
    )


@router.callback_query(F.data.startswith("gdpr_know:"))
async def on_gdpr_knowledge(callback: CallbackQuery) -> None:
    """Обработка ответа на вопрос о знании GDPR."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    
    answer = callback.data.split(":")[1]  # "unknown", "yes", "no"
    
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    if answer == "unknown":
        # Не знает → запускаем логический квест (Phase 0)
        await callback.message.answer(
            "Хорошо, давайте определим это вместе\\!",
            parse_mode="MarkdownV2",
        )
        await send_logic_question_start_callback(callback, state)
    
    elif answer == "yes":
        # Точно знает, что применяется → сразу в Phase 1 (Triggers)
        state["gdpr_status"] = "mandatory"
        state["state"] = STATE_TRIGGERS
        await callback.message.answer(
            "⚖️ *GDPR применяется*\n\n"
            "Отлично, тогда перейдем к профилированию вашего проекта\\.",
            parse_mode="MarkdownV2",
            reply_markup=kb_start_triggers(),
        )
    
    else:  # answer == "no"
        # Точно знает, что НЕ применяется → завершаем
        state["gdpr_status"] = "anonymous"
        await callback.message.answer(
            "👌 *Ну и ладно, пока\\!*\n\n"
            "Если передумаете или захотите перепроверить — нажмите /start",
            parse_mode="MarkdownV2",
        )


# === Phase 0: Logic GDPR Quest ===


async def send_logic_question_start_callback(callback: CallbackQuery, state: dict) -> None:
    """Отправить первый вопрос логического квеста (для CallbackQuery)."""
    node_id = state["logic_node"]
    node = get_logic_node(node_id)
    
    if not node:
        await callback.message.answer("⚠️ Ошибка: узел не найден. Начните заново с /start")
        return
    
    state["logic_path"].append(node_id)
    
    text = f"🧩 *Применимость GDPR*\n\n{_escape_md(node['question'])}"
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_yes_no_info("lg"))


async def send_logic_question(callback: CallbackQuery, state: dict) -> None:
    """Отправить следующий вопрос логического квеста (для CallbackQuery)."""
    node_id = state["logic_node"]
    node = get_logic_node(node_id)
    
    if not node:
        await callback.message.answer("⚠️ Ошибка: узел не найден. Начните заново с /start")
        return
    
    state["logic_path"].append(node_id)
    
    text = f"🧩 *Применимость GDPR*\n\n{_escape_md(node['question'])}"
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_yes_no_info("lg"))


@router.callback_query(F.data.startswith("lg:"))
async def on_logic_answer(callback: CallbackQuery) -> None:
    """Обработка ответа в логическом квесте."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    
    action = callback.data.split(":")[1]  # "yes", "no", или "info"
    node = get_logic_node(state["logic_node"])
    
    if not node:
        await callback.answer("Ошибка: узел не найден")
        return
    
    if action == "info":
        # Показать подсказку
        hint = node.get("hint") or "Подсказка недоступна."
        await callback.answer()
        await callback.message.answer(f"ℹ️ *Подсказка:*\n\n{_escape_md(hint)}", parse_mode="MarkdownV2")
        return
    
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    # Определить следующий узел
    next_node = node["next_yes"] if action == "yes" else node["next_no"]
    
    # Обработка специальных узлов
    if next_node == "EXIT_ANON":
        state["gdpr_status"] = "anonymous"
        await send_gdpr_not_applicable(callback, state)
    elif next_node == "EXIT_GDPR":
        state["gdpr_status"] = "mandatory"
        await send_gdpr_applicable(callback, state)
    elif next_node == "WARN_ATTACK":
        # Предупреждение о необходимости тестов
        state["gdpr_status"] = "mandatory"
        await callback.message.answer(
            "⚠️ *Внимание\\!*\n\n"
            "Без проведения атак на извлечение данных анонимность модели не считается подтверждённой\\.\n\n"
            "Мы продолжим как *GDPR применим*\\. Рекомендуется провести тесты "
            "\\(Model Inversion, Membership Inference\\)\\.\n\n"
            "Как пример, [позиция французского регулятора CNIL](https://www.cnil.fr/fr/node/167980)\\.",
            parse_mode="MarkdownV2",
            reply_markup=kb_warn_continue(),
        )
    else:
        # Переход к следующему вопросу
        state["logic_node"] = next_node
        await send_logic_question(callback, state)


@router.callback_query(F.data == "warn_continue")
async def on_warn_continue(callback: CallbackQuery) -> None:
    """Продолжение после предупреждения WARN_ATTACK."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await send_gdpr_applicable(callback, state)


async def send_gdpr_not_applicable(callback: CallbackQuery, state: dict) -> None:
    """GDPR не применяется - аудит не требуется, завершаем."""
    text = (
        "🏆 *GDPR НЕ ПРИМЕНЯЕТСЯ*\n\n"
        "Поздравляю\\! Ваша модель признана анонимной\\.\n\n"
        "К ней не применяются требования GDPR по защите персональных данных\\.\n\n"
        "Аудит не требуется\\. Вы можете сосредоточиться на общих мерах безопасности "
        "и требованиях AI Act \\(при необходимости\\)\\.\n\n"
        "📋 *Важно:* Документация должна позволять регуляторам и пользователям "
        "убедиться, что модель не обрабатывает персональные данные\\."
    )
    
    # Не переходим к триггерам - завершаем сессию
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_audit_not_required())


async def send_gdpr_applicable(callback: CallbackQuery, state: dict) -> None:
    """GDPR применяется - переходим к триггерам."""
    text = (
        "⚖️ *GDPR ПРИМЕНЯЕТСЯ*\n\n"
        "Ваша модель признана носителем персональных данных\\.\n\n"
        "Теперь нужно определить ваш профиль и роль в проекте, "
        "чтобы сформировать персональный чек\\-лист мер\\."
    )
    
    state["state"] = STATE_TRIGGERS
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_start_triggers())


# === Phase 1: Triggers ===
@router.callback_query(F.data == "start_triggers")
async def on_start_triggers(callback: CallbackQuery) -> None:
    """Начало опроса триггеров."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    state["state"] = STATE_TRIGGERS
    state["trigger_index"] = 0
    
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await send_trigger_question(callback, state)


async def send_trigger_question(message_or_callback, state: dict) -> None:
    """Отправить следующий вопрос триггера."""
    triggers = load_system_triggers()
    idx = state["trigger_index"]
    
    if idx >= len(triggers):
        # Все триггеры пройдены - показать резюме
        await send_profile_summary(message_or_callback, state)
        return
    
    trigger = triggers[idx]
    text = f"❓ *Вопрос {idx + 1}/{len(triggers)}*\n\n{_escape_md(trigger['question_text'])}"
    kb = kb_yes_no("trg", trigger["variable"])
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, parse_mode="MarkdownV2", reply_markup=kb)
    else:
        await message_or_callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb)


async def send_profile_summary(message_or_callback, state: dict) -> None:
    """Показать резюме профиля после триггеров."""
    profile = state["profile"]
    
    # Формируем текст резюме на основе заполненных переменных
    lines = ["⚙️ *Профиль настроен\\!*\n"]
    
    # Роли (новые триггеры)
    if profile.get("is_creator"):
        lines.append("• 🔧 Роль: Разработчик модели \\(Model Developer\\)")
    if profile.get("is_brand_owner"):
        lines.append("• 🔧 Роль: Оператор AI\\-системы \\(AI System Operator\\)/Владелец продукта")
    if profile.get("is_modifier"):
        lines.append("• 🔧 Роль: Лицо, модифицирующее модель")
    
    # Характеристики (старые триггеры)
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
    
    lines.append("\nТеперь перейдем к персональному чек\\-листу мер\\.")
    
    text = "\n".join(lines)
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, parse_mode="MarkdownV2", reply_markup=kb_start_checklist())
    else:
        await message_or_callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_start_checklist())


@router.callback_query(F.data.startswith("trg:"))
async def on_trigger_answer(callback: CallbackQuery) -> None:
    """Обработка ответа на триггер."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    
    parts = callback.data.split(":")
    answer = parts[1]  # "yes" или "no"
    variable = parts[2] if len(parts) > 2 else ""
    
    # Записываем ответ в профиль (поддержка любых переменных)
    if variable:
        state["profile"][variable] = (answer == "yes")
    
    state["trigger_index"] += 1
    
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await send_trigger_question(callback, state)


# === Phase 2: Checklist ===
@router.callback_query(F.data == "start_checklist")
async def on_start_checklist(callback: CallbackQuery) -> None:
    """Начало чек-листа мер."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    
    # Отфильтровать меры по профилю
    items = filter_content_by_profile(state["profile"], state["gdpr_status"] or "mandatory")
    state["content_items"] = items
    state["content_index"] = 0
    state["content_done"] = set()
    state["content_skipped"] = set()
    state["state"] = STATE_CHECKLIST
    
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    
    total = len(items)
    await callback.message.answer(
        f"📋 *Ваш персональный чек\\-лист готов\\!*\n\n"
        f"Всего мер к проверке: *{total}*\n\n"
        f"Пройдите по каждому пункту, отмечая выполненные меры\\.",
        parse_mode="MarkdownV2",
    )
    
    await send_checklist_item(callback, state)


async def send_checklist_item(callback: CallbackQuery, state: dict) -> None:
    """Отправить текущий пункт чек-листа."""
    items = state["content_items"]
    idx = state["content_index"]
    
    if idx >= len(items):
        # Все пункты пройдены
        state["state"] = STATE_REPORT
        await send_report(callback, state)
        return
    
    item = items[idx]
    total = len(items)
    done = len(state["content_done"])
    
    text = (
        f"📌 *Пункт {idx + 1}/{total}* \\| Выполнено: {done}\n"
        f"🤹 {_escape_md(item['sheet'])}\n\n"
        f"*{_escape_md(item['id'])}*: {_escape_md(item['requirement'])}"
    )
    
    await callback.message.answer(text, parse_mode="MarkdownV2", reply_markup=kb_checklist_item(item["id"]))


@router.callback_query(F.data.startswith("ch:"))
async def on_checklist_action(callback: CallbackQuery) -> None:
    """Обработка действий в чек-листе."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    
    parts = callback.data.split(":")
    action = parts[1]  # "done", "info", "skip", "progress", "continue"
    item_id = parts[2] if len(parts) > 2 else ""
    
    if action == "progress":
        # Показать прогресс
        await show_progress(callback, state)
        return
    
    if action == "continue":
        await callback.answer()
        await send_checklist_item(callback, state)
        return
    
    if action == "info":
        # Показать подробности
        item = _find_item_by_id(state["content_items"], item_id)
        if item:
            hint = item.get("detailed_hint") or "Подробная информация недоступна."
            await callback.answer()
            await callback.message.answer(f"ℹ️ *Подробнее:*\n\n{_escape_md(hint)}", parse_mode="MarkdownV2")
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


# === Phase 3: Report ===
async def send_report(callback: CallbackQuery, state: dict) -> None:
    """Отправить финальный отчет."""
    report = generate_report(state)
    
    # Разбить на части, если слишком длинный
    if len(report) > 4000:
        parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await callback.message.answer(part, parse_mode="MarkdownV2", reply_markup=kb_report())
            else:
                await callback.message.answer(part, parse_mode="MarkdownV2")
    else:
        await callback.message.answer(report, parse_mode="MarkdownV2", reply_markup=kb_report())


def generate_report(state: dict) -> str:
    """Генерация финального отчета."""
    profile = state["profile"]
    gdpr_status = state.get("gdpr_status") or "unknown"
    items = state["content_items"]
    done = state["content_done"]
    skipped = state["content_skipped"]
    
    total = len(items)
    done_count = len(done)
    skipped_count = len(skipped)
    percent = int((done_count / total) * 100) if total > 0 else 0
    
    # Профиль - роли
    roles = []
    if profile.get("is_creator"):
        roles.append("Разработчик модели")
    if profile.get("is_brand_owner"):
        roles.append("Оператор/Владелец продукта")
    if profile.get("is_modifier"):
        roles.append("Модификатор модели")
    roles_text = ", ".join(roles) if roles else "Не определено"
    
    # Профиль - характеристики
    gdpr_text = "GDPR Mandatory" if gdpr_status == "mandatory" else "Anonymous"
    child_text = "Да" if profile.get("is_child") else "Нет"
    if profile.get("is_gen_ai"):
        type_text = "Генеративный ИИ (есть риски «галлюцинаций»)"
    else:
        type_text = "Классический ML"
    if profile.get("is_high_risk"):
        risk_text = "Потенциально высокий риск (требует подтверждения)"
    else:
        risk_text = "Обязательства по прозрачности"
    source_text = "Веб\\-скрейпинг" if profile.get("has_scraping") else "Приватный датасет"
    
    # Пропущенные пункты
    skipped_items = [item for item in items if item["id"] in skipped]
    skipped_text = ""
    for item in skipped_items:
        skipped_text += f"• 🔸 *{_escape_md(item['id'])}*: {_escape_md(item['requirement'])}\n"
    if not skipped_text:
        skipped_text = "Все пункты выполнены\\! 🎉\n"
    
    # Динамический комментарий
    legal_comment = ""
    if gdpr_status == "mandatory":
        legal_comment = (
            "💡 Твой ИИ как губка, он впитал данные реальных людей\\. "
            "По GDPR, если человек попросит «забыть» его, ты не можешь просто развести руками\\. "
            "Тебе нужно заранее продумать, как ты удалишь его из «памяти» модели "
            "\\(через фильтры или переобучение\\)\\. Это самая сложная часть, начни с неё\\."
        )
    else:
        legal_comment = (
            "💡 Поздравляем, ты прошел по самому легкому пути\\! "
            "Раз данные анонимны, GDPR к тебе почти не применим\\. "
            "Теперь твоя главная задача — следить, чтобы хакеры не украли саму модель\\. "
            "Если они взломают твой API, они могут попытаться восстановить личности людей через хитрые запросы\\."
        )
    
    if profile.get("is_child"):
        legal_comment += (
            "\n\n💡 С детьми закон работает в режиме «максимальной осторожности»\\. "
            "Ты не имеешь права писать для них скучные правила на 20 страниц\\. "
            "Тебе нужно нарисовать понятные иконки или снять короткое видео о том, как работает твой проект\\. "
            "И обязательно поставь барьер \\(Age Verification\\), чтобы дети не попадали туда, где им не место\\."
        )
    
    if profile.get("has_scraping"):
        legal_comment += (
            "\n\n💡 Данные из интернета не «ничейные»\\. "
            "Убедись, что ты не спарсил то, что запрещено владельцами сайтов \\(robots\\.txt\\), "
            "иначе могут прилететь иски за нарушение авторских прав\\."
        )
    
    # Дата
    date_str = datetime.now().strftime("%d\\.%m\\.%Y")
    
    report = f"""🏁 *Аудит завершен\\!*
    Отчёт носит справочный и диагностический характер и не является юридическим заключением, официальной оценкой или подтверждением соответствия требованиям законодательства\\.
📅 Дата: {date_str}

*1\\. Профиль проекта:*
• ⚖️ Статус GDPR: *{_escape_md(gdpr_text)}*
• 👤 Роль: {_escape_md(roles_text)}
• 🤖 Тип системы: {_escape_md(type_text)}
• 👶 Несовершеннолетние пользователи: {_escape_md(child_text)}
• 🚩 Категория по AI Act: {_escape_md(risk_text)}
• 🌐 Метод сбора: {source_text}

*2\\. Итоги проверки:*
📊 Выполнено: *{percent}%*
✅ Внедрено мер: {done_count}
⚠️ Требуют внимания: {skipped_count}

*3\\. Задачи к исполнению:*
{skipped_text}
*4\\. Комментарий:*
{legal_comment}

*5\\. Рекомендуемые следующие шаги:*
1\\. Устранить пропуски, отмеченные выше
2\\. Провести атаку на извлечение данных \\(если ещё не сделано\\)
3\\. Сформировать DPIA \\(Оценку воздействия на данные\\)"""
    
    return report


@router.callback_query(F.data == "report:gemini")
async def on_report_gemini(callback: CallbackQuery) -> None:
    """Обработка запроса к Gemini (заглушка)."""
    await callback.answer()
    await callback.message.answer(
        "🤖 *Gemini AI Expert*\n\n"
        "Функция консультации с ИИ\\-экспертом находится в разработке\\.\n\n"
        "В будущей версии вы сможете задать вопросы по результатам аудита\\.",
        parse_mode="MarkdownV2",
    )


@router.callback_query(F.data == "report:restart")
async def on_report_restart(callback: CallbackQuery) -> None:
    """Начать новый аудит."""
    user_id = callback.from_user.id
    reset_state(user_id)
    
    await callback.answer("Начинаем новый аудит!")
    await callback.message.edit_reply_markup(reply_markup=None)
    
    await callback.message.answer(
        "🔄 *Новый аудит*\n\n"
        "Знаете ли вы, применяется ли GDPR к вашей модели?",
        parse_mode="MarkdownV2",
        reply_markup=kb_gdpr_knowledge(),
    )


# === Helpers ===
def _escape_md(text: str) -> str:
    """Экранировать специальные символы для MarkdownV2."""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


def _find_item_by_id(items: list[dict], item_id: str) -> Optional[dict]:
    """Найти пункт по ID."""
    for item in items:
        if item["id"] == item_id:
            return item
    return None


# === Bot Setup ===
def create_bot() -> tuple[Bot, Dispatcher]:
    """Создать бота и диспетчер."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Укажите TELEGRAM_BOT_TOKEN в .env")
    
    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(router)
    return bot, dp


async def run_polling() -> None:
    """Запустить бота в режиме polling."""
    bot, dp = create_bot()
    await dp.start_polling(bot)
