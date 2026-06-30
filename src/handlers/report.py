"""Обработчики финального отчета и отзывов (Фаза 3)."""

from datetime import datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from ..analytics import log_event
from ..formatting import progress_block
from ..keyboards import kb_gdpr_knowledge, kb_report
from ..reporting import generate_report
from ..reviews import save_review
from ..state import STATE_REPORT, STATE_REVIEW, get_state, reset_state

router = Router()


async def send_report(callback: CallbackQuery, state: dict) -> None:
    """Отправить финальный отчет."""
    log_event(callback.from_user, phase="phase_3", event="phase_3_started", state=state)
    await callback.message.answer(progress_block(3), parse_mode="MarkdownV2")

    report = generate_report(state)

    if len(report) > 4000:
        parts = [report[i:i + 4000] for i in range(0, len(report), 4000)]
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                await callback.message.answer(part, parse_mode="MarkdownV2", reply_markup=kb_report())
            else:
                await callback.message.answer(part, parse_mode="MarkdownV2")
    else:
        await callback.message.answer(report, parse_mode="MarkdownV2", reply_markup=kb_report())


@router.callback_query(F.data == "report:review")
async def on_report_review(callback: CallbackQuery) -> None:
    """Запрос отзыва от пользователя."""
    user_id = callback.from_user.id
    state = get_state(user_id)
    state["state"] = STATE_REVIEW

    await callback.answer()
    await callback.message.answer(
        "📝 *Оставьте отзыв*\n\n"
        "Напишите ваш отзыв текстовым сообщением\\.\n"
        "Он поможет нам улучшить бота\\!",
        parse_mode="MarkdownV2",
    )


@router.message(F.text)
async def on_text_message(message: Message) -> None:
    """Обработка текстовых сообщений (отзыв)."""
    user_id = message.from_user.id if message.from_user else 0
    state = get_state(user_id)

    if state["state"] != STATE_REVIEW:
        return

    review_text = (message.text or "").strip()
    if review_text.startswith("/"):
        return
    if not review_text:
        await message.answer("Пожалуйста, напишите текст отзыва\\.", parse_mode="MarkdownV2")
        return

    username = message.from_user.username if message.from_user and message.from_user.username else f"id{user_id}"
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    save_review(username, review_text, date_str)

    state["state"] = STATE_REPORT

    await message.answer(
        "✅ *Спасибо за отзыв\\!*\n\n"
        "Ваше мнение очень важно для нас\\.",
        parse_mode="MarkdownV2",
        reply_markup=kb_report(),
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
