"""Генерация финального отчета."""

from datetime import datetime

from .formatting import escape_md

ANON_DOCUMENTATION_DISCLAIMER = (
    "Документация должна позволять регуляторам и пользователям убедиться, "
    "что модель не обрабатывает персональные данные."
)

PROHIBITED_LEGAL_COMMENT = (
    "⚠️ Внимание! Ваша система использует методы, которые полностью запрещены "
    "на территории Европейского Союза (согласно Статье 5 AI Act). Коммерческий запуск, "
    "дистрибуция или использование данной технологии в ЕС повлекут за собой оборотные "
    "штрафы до 35 млн евро или 7% от глобального годового дохода. Проект требует "
    "радикального изменения концепции до начала разработки."
)


def _numbered_steps(steps: list[str]) -> str:
    """Сформировать MarkdownV2-нумерацию следующих шагов."""
    return "\n".join(f"{idx}\\. {escape_md(step)}" for idx, step in enumerate(steps, start=1))


def _is_prohibited(state: dict, profile: dict) -> bool:
    """Определить терминальный prohibited-сценарий."""
    return (
        state.get("global_status") == "PROHIBITED_RISK"
        or state.get("ai_act_status") == "PROHIBITED_RISK"
        or bool(profile.get("is_prohibited"))
        or bool(profile.get("prohibited_type"))
    )


def _role_text(profile: dict, is_out_of_scope: bool) -> str:
    """Собрать роль для профиля проекта."""
    if is_out_of_scope:
        return "Вне зоны регулирования AI Act (опрос не проводился)"

    roles = []
    if profile.get("is_creator"):
        roles.append("Разработчик модели")
    if profile.get("is_brand_owner"):
        roles.append("Оператор/Владелец продукта")
    if profile.get("is_modifier"):
        roles.append("Модификатор модели")
    return ", ".join(roles) if roles else "Не определено"


def _risk_text(profile: dict, target: str | None, is_out_of_scope: bool, is_prohibited: bool) -> str:
    """Собрать категорию риска AI Act."""
    if is_prohibited:
        return "🔴 Запрещенная практика (Prohibited - ст. 5 AI Act)"
    if is_out_of_scope:
        return "Не применимо (Out of Scope)"
    if profile.get("is_high_risk"):
        return "🔥 Высокий риск (High-Risk System)"
    if profile.get("is_gen_ai"):
        return "🤖 Модель общего назначения (General Purpose AI / GPAI)"
    if target == "model":
        return "Продуктовые категории риска не применялись к независимой модели"
    return "Обязательства по прозрачности"


def _next_steps(profile: dict, is_out_of_scope: bool, is_prohibited: bool) -> str:
    """Собрать динамические следующие шаги."""
    if is_prohibited:
        return escape_md("Не формируются до радикального изменения концепции проекта.")

    if not is_out_of_scope and (profile.get("is_high_risk") or profile.get("is_gen_ai")):
        return _numbered_steps([
            "Подготовить техническую документацию для нотифицированного органа ЕС",
            "Пройти процедуру оценки соответствия (Conformity Assessment)",
            "Внести систему в официальную базу данных ИИ в ЕС",
        ])

    return _numbered_steps([
        "Разработать GDPR Privacy Policy",
        "Оформить реестр обработки данных (ROPA)",
        "Настроить процесс обработки запросов субъектов данных",
    ])


def generate_report(state: dict) -> str:
    """Генерация финального отчета."""
    profile = state.get("profile", {})
    gdpr_status = state.get("gdpr_status") or "unknown"
    gdpr_mandatory = state.get("gdpr_mandatory")
    items = state.get("content_items", [])
    done = state.get("content_done", set())
    skipped = state.get("content_skipped", set())

    total = len(items)
    done_count = len(done)
    skipped_count = len(skipped)
    percent = int((done_count / total) * 100) if total > 0 else 0

    if gdpr_mandatory is None:
        gdpr_mandatory = gdpr_status == "mandatory"

    gdpr_text = "GDPR Mandatory" if gdpr_mandatory else "Anonymous"
    target = state.get("ai_type") or state.get("target")
    target_text = "Готовое приложение/система" if target == "system" else "Независимая модель"
    if target not in {"system", "model"}:
        target_text = "Не определено"
    ai_act_status = state.get("ai_act_status")
    if ai_act_status == "in_scope":
        ai_act_text = "В сфере AI Act"
    elif ai_act_status == "PROHIBITED_RISK":
        ai_act_text = "PROHIBITED_RISK"
    elif ai_act_status == "AIA_OUT_OF_SCOPE":
        ai_act_text = "AIA_OUT_OF_SCOPE"
    else:
        ai_act_text = "Не определено"
    is_out_of_scope = ai_act_status == "AIA_OUT_OF_SCOPE"
    is_prohibited = _is_prohibited(state, profile)
    roles_text = _role_text(profile, is_out_of_scope)
    child_text = "Да" if profile.get("is_child") else "Нет"
    if profile.get("is_gen_ai"):
        type_text = "Генеративный ИИ (есть риски «галлюцинаций»)"
    else:
        type_text = "Классический ML"
    risk_text = _risk_text(profile, target, is_out_of_scope, is_prohibited)
    source_text = "Веб\\-скрейпинг" if profile.get("has_scraping") else "Приватный датасет"

    if is_prohibited:
        total = 0
        done_count = 0
        skipped_count = 0
        percent = 0
        skipped_text = "Стандартные технические и продуктовые задачи не формируются для запрещенной практики\\.\n"
    else:
        skipped_items = [item for item in items if item["id"] in skipped]
        skipped_text = ""
        for item in skipped_items:
            skipped_text += f"• 🔸 {escape_md(item['requirement'])}\n"
        if not items and ai_act_status == "AIA_OUT_OF_SCOPE":
            skipped_text = "По условиям Content\\_Checklist обязательные задачи не найдены\\.\n"
        elif not skipped_text:
            skipped_text = "Все пункты выполнены\\! 🎉\n"

    legal_comment = ""
    if is_prohibited:
        legal_comment = escape_md(PROHIBITED_LEGAL_COMMENT)
    elif gdpr_mandatory:
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

        if state.get("anon_documentation_disclaimer"):
            legal_comment += f"\n\n📋 {escape_md(ANON_DOCUMENTATION_DISCLAIMER)}"

    if not is_prohibited and profile.get("is_child"):
        legal_comment += (
            "\n\n💡 С детьми закон работает в режиме «максимальной осторожности»\\. "
            "Ты не имеешь права писать для них скучные правила на 20 страниц\\. "
            "Тебе нужно нарисовать понятные иконки или снять короткое видео о том, как работает твой проект\\. "
            "И обязательно поставь барьер \\(Age Verification\\), чтобы дети не попадали туда, где им не место\\."
        )

    if not is_prohibited and profile.get("has_scraping"):
        legal_comment += (
            "\n\n💡 Данные из интернета не «ничейные»\\. "
            "Убедись, что ты не спарсил то, что запрещено владельцами сайтов \\(robots\\.txt\\), "
            "иначе могут прилететь иски за нарушение авторских прав\\."
        )

    date_str = datetime.now().strftime("%d\\.%m\\.%Y")
    next_steps = _next_steps(profile, is_out_of_scope, is_prohibited)

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
{next_steps}"""
