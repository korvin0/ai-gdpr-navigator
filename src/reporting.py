"""Генерация финального отчета."""

from datetime import datetime

from .formatting import escape_md

ANON_DOCUMENTATION_DISCLAIMER = (
    "Документация должна позволять регуляторам и пользователям убедиться, "
    "что модель не обрабатывает персональные данные."
)


def generate_report(state: dict) -> str:
    """Генерация финального отчета."""
    profile = state["profile"]
    gdpr_status = state.get("gdpr_status") or "unknown"
    gdpr_mandatory = state.get("gdpr_mandatory")
    items = state["content_items"]
    done = state["content_done"]
    skipped = state["content_skipped"]

    total = len(items)
    done_count = len(done)
    skipped_count = len(skipped)
    percent = int((done_count / total) * 100) if total > 0 else 0

    roles = []
    if profile.get("is_creator"):
        roles.append("Разработчик модели")
    if profile.get("is_brand_owner"):
        roles.append("Оператор/Владелец продукта")
    if profile.get("is_modifier"):
        roles.append("Модификатор модели")
    roles_text = ", ".join(roles) if roles else "Не определено"

    if gdpr_mandatory is None:
        gdpr_mandatory = gdpr_status == "mandatory"

    gdpr_text = "GDPR Mandatory" if gdpr_mandatory else "Anonymous"
    target = state.get("target")
    target_text = "Готовое приложение/система" if target == "system" else "Независимая модель"
    if target not in {"system", "model"}:
        target_text = "Не определено"
    ai_act_status = state.get("ai_act_status")
    ai_act_text = "В сфере AI Act" if ai_act_status == "in_scope" else "AIA_OUT_OF_SCOPE"
    if ai_act_status is None:
        ai_act_text = "Не определено"
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

    skipped_items = [item for item in items if item["id"] in skipped]
    skipped_text = ""
    for item in skipped_items:
        skipped_text += f"• 🔸 {escape_md(item['requirement'])}\n"
    if not skipped_text:
        skipped_text = "Все пункты выполнены\\! 🎉\n"

    legal_comment = ""
    if gdpr_mandatory:
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
            f"\n\n📋 {escape_md(ANON_DOCUMENTATION_DISCLAIMER)}"
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

    date_str = datetime.now().strftime("%d\\.%m\\.%Y")

    return f"""🏁 *Аудит завершен\\!*
    Отчёт носит справочный и диагностический характер и не является юридическим заключением, официальной оценкой или подтверждением соответствия требованиям законодательства\\.
📅 Дата: {date_str}

*1\\. Профиль проекта:*
• ⚖️ Статус GDPR: *{escape_md(gdpr_text)}*
• 👤 Роль: {escape_md(roles_text)}
• 🤖 Тип системы: {escape_md(type_text)}
• 🎯 Объект проверки: {escape_md(target_text)}
• 🇪🇺 Статус AI Act: {escape_md(ai_act_text)}
• 👶 Несовершеннолетние пользователи: {escape_md(child_text)}
• 🚩 Категория по AI Act: {escape_md(risk_text)}
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
