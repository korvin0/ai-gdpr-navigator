"""Обработчики старта и предварительного вопроса о GDPR."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from ..formatting import progress_block
from ..keyboards import kb_gdpr_knowledge
from ..state import get_state, reset_state
from .ai_act import start_ai_act_screening
from .logic import send_logic_question_start_callback

router = Router()


@router.message(Command("start"))
@router.message(Command("cancel"))
async def cmd_start(message: Message) -> None:
    """Начало или перезапуск бота."""
    user_id = message.from_user.id if message.from_user else 0
    reset_state(user_id)

    await message.answer(
        "👋 *Добро пожаловать в AI&GDPR Compliance Navigator\\!*\n"
        "Я помогу проверить ваш ИИ\\-проект на соответствие нормам GDPR и AI Act\\.\n"
        "_Результаты работы бота носят справочный характер и основаны на информации, предоставленной пользователем\\. Окончательная правовая квалификация требует отдельного анализа экспертами\\._\n\n"
        "Начнем проверку вашего продукта?",
        parse_mode="MarkdownV2",
        reply_markup=kb_gdpr_knowledge(),
    )


@router.callback_query(F.data.startswith("gdpr_know:"))
async def on_gdpr_knowledge(callback: CallbackQuery) -> None:
    """Обработка ответа на вопрос о знании GDPR."""
    user_id = callback.from_user.id
    state = get_state(user_id)

    answer = callback.data.split(":")[1]

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    if answer == "unknown":
        await callback.message.answer(
            "Давайте определим вместе, какие европейские правила регулируют ваш ИИ\\-продукт\\!\n\n"
            f"{progress_block(0)}",
            parse_mode="MarkdownV2",
        )
        await send_logic_question_start_callback(callback, state)

    elif answer == "yes":
        state["gdpr_status"] = "mandatory"
        state["gdpr_mandatory"] = True
        await start_ai_act_screening(callback, state)

    else:
        state["gdpr_status"] = "anonymous"
        state["gdpr_mandatory"] = False
        await start_ai_act_screening(callback, state)
