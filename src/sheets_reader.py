"""
Чтение 4 вкладок Google Sheets: Logic_GDPR, Content_Checklist, System_Triggers, Gemini_KB.
Использует опубликованные CSV URL (Файл -> Опубликовать в интернете -> CSV).
"""
import ast
import csv
import os
import re
from typing import Optional
from urllib.request import urlopen

# === CSV URLs для каждой вкладки ===
DEFAULT_CSV_LOGIC_GDPR = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=2046117556&single=true&output=csv"
DEFAULT_CSV_CONTENT_CHECKLIST = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=1062279979&single=true&output=csv"
DEFAULT_CSV_SYSTEM_TRIGGERS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=1004258855&single=true&output=csv"
DEFAULT_CSV_GEMINI_KB = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=1940152089&single=true&output=csv"

DEFAULT_PROHIBITED_PRACTICES = [
    "Скрытое воздействие на подсознание",
    "Social scoring",
    "Массовый скрейпинг лиц из интернета/камер для распознавания",
    "Оценка эмоций на рабочем месте/в учебных заведениях",
    "Оценка риска совершения преступлений физлицами на основе профилирования/черт характера",
]

ROLE_SHIFT_WARNING = (
    "\n\n⚠️ Внимание: Так как вы модифицируете модель или выводите её под своим брендом, "
    "согласно ст. 25 AI Act происходит 'Сдвиг роли' (Role Shift). Вы несете юридическую "
    "ответственность в ЕС не как простой пользователь (Deployer), а как Поставщик (Provider) "
    "ИИ-системы."
)

ROLE_SHIFT_MARKERS = (
    "правовой статус сторон",
    "контролер vs процессор",
    "контроллер vs процессор",
    "контролер",
    "контролёр",
    "контроллер",
    "процессор",
    "controller",
    "processor",
    "provider",
    "поставщик",
)

BOOLEAN_TRIGGER_VARIABLES = {
    "always",
    "gdpr_mandatory",
    "attack_risk",
    "anon_documentation_disclaimer",
    "is_gen_ai",
    "prohibited_type",
    "is_prohibited",
    "is_child",
    "has_scraping",
    "is_high_risk",
    "is_creator",
    "is_brand_owner",
    "is_modifier",
}

PRODUCT_RISK_FLAGS = {"is_high_risk", "is_child", "prohibited_type", "is_prohibited"}

ALLOWED_TRIGGER_AST_NODES = (
    ast.Expression,
    ast.BoolOp,
    ast.UnaryOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Eq,
    ast.NotEq,
)


def _get_url(env_key: str, default: str) -> str:
    """Получить URL из env или использовать default."""
    return (os.getenv(env_key) or "").strip() or default


def _fetch_csv(url: str) -> list[dict]:
    """Скачать и распарсить CSV."""
    with urlopen(url, timeout=15) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    return list(csv.DictReader(text.splitlines()))


def _s(value, default: str = "") -> str:
    """Безопасное приведение к строке и strip."""
    if value is None:
        return default
    return str(value).strip() or default


def _split_options(value: str) -> list[str]:
    """Разобрать список вариантов из ячейки Google Sheets."""
    text = _s(value)
    if not text:
        return []

    for separator in ("|", ";", "\n", "⬜"):
        text = text.replace(separator, "\n")

    result = []
    for item in text.splitlines():
        cleaned = item.strip(" \t\r\n-•0123456789.)")
        if cleaned:
            result.append(cleaned)
    return result


# === System_Triggers (Фаза 0) ===
def load_system_triggers() -> list[dict]:
    """
    Загружает триггеры для Фазы 0.
    Возвращает: [{"variable": "is_gen_ai", "question_text": "...", "ui_type": "Yes/No Buttons", "hint": "...", "options": [...]}, ...]
    """
    url = _get_url("CSV_URL_SYSTEM_TRIGGERS", DEFAULT_CSV_SYSTEM_TRIGGERS)
    try:
        rows = _fetch_csv(url)
        result = []
        for row in rows:
            variable = _s(row.get("Variable (Ключ)") or row.get("Variable") or row.get("Ключ"))
            question = _s(row.get("Question_Text (Вопрос бота)") or row.get("Question_Text") or row.get("Вопрос бота"))
            ui_type = _s(row.get("UI_Type") or row.get("UI Type"), "Yes/No Buttons")
            hint = _s(row.get("Hint (Подсказка для кнопки \"Инфо\")") or row.get("Hint") or row.get("Подсказка"))
            options = _split_options(
                row.get("Options")
                or row.get("Options (Варианты)")
                or row.get("Checkbox_Options")
                or row.get("Checkbox Options")
                or row.get("Варианты")
                or ""
            )
            if not hint:
                for k, v in row.items():
                    if "Hint" in k or "Подсказка" in k:
                        hint = _s(v)
                        if hint:
                            break
            if variable == "prohibited_type" and not options:
                options = DEFAULT_PROHIBITED_PRACTICES
            if variable and question:
                result.append({
                    "variable": variable,
                    "question_text": question,
                    "ui_type": ui_type,
                    "hint": hint,
                    "options": options,
                })
        return result
    except Exception:
        # Fallback данные
        return [
            {"variable": "is_gen_ai", "question_text": "Это Генеративный ИИ (текст, изображения, видео)?", "ui_type": "Yes/No Buttons", "hint": "Генеративный ИИ создаёт новый контент (текст, изображения, видео) на основе обучающих данных."},
            {"variable": "prohibited_type", "question_text": "Использует ли ваша ИИ-система практики, которые полностью запрещены на территории Европейского союза?", "ui_type": "Yes/No Buttons", "hint": "", "options": DEFAULT_PROHIBITED_PRACTICES},
            {"variable": "is_child", "question_text": "Проект ориентирован на детей до 18 лет?", "ui_type": "Yes/No Buttons", "hint": "Если среди пользователей могут быть несовершеннолетние, применяются усиленные меры защиты."},
            {"variable": "has_scraping", "question_text": "Вы используете веб-скрейпинг для сбора данных?", "ui_type": "Yes/No Buttons", "hint": "Веб-скрейпинг — автоматический сбор данных с сайтов. Требует проверки прав и robots.txt."},
            {"variable": "is_high_risk", "question_text": "ИИ используется в критической сфере (HR, медицина)?", "ui_type": "Yes/No Buttons", "hint": "Системы высокого риска по AI Act: HR, медицина, правосудие, образование, биометрия."},
        ]


# === Logic_GDPR (Фаза 0: Block L + Block M) ===
def load_logic_gdpr() -> list[dict]:
    """
    Загружает логику входного скрининга для Фазы 0.
    Возвращает: [{"id": "L1", "question": "...", "hint": "...", "next_yes": "L2", "next_no": "M1"}, ...]
    Вкладка содержит GDPR Block L (L1-L4) и тексты вопросов AI Act Block M (M1-M2).
    """
    url = _get_url("CSV_URL_LOGIC_GDPR", DEFAULT_CSV_LOGIC_GDPR)
    # Также поддержка старой переменной CSV_URL
    if not os.getenv("CSV_URL_LOGIC_GDPR"):
        old_url = os.getenv("CSV_URL")
        if old_url and old_url.strip():
            url = old_url.strip()
    
    try:
        rows = _fetch_csv(url)
        result = []
        for row in rows:
            id_ = _s(row.get("ID") or row.get("id"))
            if not id_:
                continue
            question = _s(row.get("Question (Вопрос)") or row.get("Question") or row.get("Вопрос"))
            hint = _s(row.get("Hint (Подсказка для кнопки \"Инфо\")") or row.get("Hint") or row.get("Подсказка"))
            # Попробуем найти hint в любой колонке с "Hint" или "Подсказка"
            if not hint:
                for k, v in row.items():
                    if "Hint" in k or "Подсказка" in k:
                        hint = _s(v)
                        if hint:
                            break
            next_yes = _s(row.get("Next_If_Yes") or row.get("Next If Yes"))
            next_no = _s(row.get("Next_If_No") or row.get("Next If No"))
            result.append({
                "id": id_,
                "question": question,
                "hint": hint,
                "next_yes": next_yes,
                "next_no": next_no,
            })
        return result
    except Exception:
        # Fallback данные
        return [
            {"id": "L1", "question": "Содержит ли датасет персональные данные (ПД)?", "hint": "ПД — любая инфо о человеке (email, ID, фото, скрейпинг).", "next_yes": "L2", "next_no": "M1"},
            {"id": "L2", "question": "Модель создана для поиска/выдачи инфо о лицах?", "hint": "Например: распознавание лиц или генерация досье.", "next_yes": "M1", "next_no": "L3"},
            {"id": "L3", "question": "Проводились ли атаки на извлечение ПД из весов?", "hint": "Проверка, можно ли \"вытащить\" данные через API модели.", "next_yes": "L4", "next_no": "M1"},
            {"id": "L4", "question": "Риск ре-идентификации признан ничтожным?", "hint": "Если вероятность восстановления ПД из модели близка к 0.", "next_yes": "M1", "next_no": "M1"},
        ]


def get_logic_node(node_id: str) -> Optional[dict]:
    """Получить узел логики по ID."""
    nodes = load_logic_gdpr()
    for node in nodes:
        if node["id"] == node_id:
            return node
    return None


# === Content_Checklist (Фаза 2) ===
def load_content_checklist() -> list[dict]:
    """
    Загружает чек-лист мер для Фазы 2.
    Возвращает: [{"id": "1.1", "sheet": "Блок А", "requirement": "...", "trigger_variable": "always", "detailed_hint": "..."}, ...]
    """
    url = _get_url("CSV_URL_CONTENT_CHECKLIST", DEFAULT_CSV_CONTENT_CHECKLIST)
    try:
        rows = _fetch_csv(url)
        result = []
        for row in rows:
            id_ = _s(row.get("ID") or row.get("id"))
            sheet = _s(row.get("Sheet") or row.get("Блок"))
            requirement = _s(row.get("Requirement (Требование)") or row.get("Requirement") or row.get("Требование"))
            trigger_var = _s(row.get("Trigger_Variable (Условие)") or row.get("Trigger_Variable") or row.get("Условие"), "always")
            detailed_hint = _s(row.get("Detailed_Hint (Инфо-блок)") or row.get("Detailed_Hint") or row.get("Инфо-блок"))
            # Попробуем найти hint в любой колонке с "Hint" или "Инфо"
            if not detailed_hint:
                for k, v in row.items():
                    if "Hint" in k or "Инфо" in k:
                        detailed_hint = _s(v)
                        if detailed_hint:
                            break
            if id_ or requirement:
                result.append({
                    "id": id_ or f"M{len(result)}",
                    "sheet": sheet,
                    "requirement": requirement or id_,
                    "trigger_variable": trigger_var.strip(),
                    "detailed_hint": detailed_hint,
                })
        return result
    except Exception:
        # Fallback данные
        return [
            {"id": "1.1", "sheet": "Блок А", "requirement": "Определить роль: Контроллер или Процессор.", "trigger_variable": "always", "detailed_hint": "См. Лист 2: Определите, кто несет ответственность."},
            {"id": "10.1", "sheet": "Блок Г", "requirement": "Использовать формат весов safetensors.", "trigger_variable": "is_gen_ai", "detailed_hint": "Защита от выполнения произвольного кода."},
        ]


def _to_bool(value) -> bool:
    """Привести значение из сессии/CSV к bool для eval-контекста."""
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "да"}:
            return True
        if normalized in {"false", "0", "no", "n", "нет", ""}:
            return False
    return bool(value)


def _build_trigger_context(state: dict, profile: dict) -> dict:
    """Собрать типизированный контекст для выражений Trigger_Variable."""
    context = {name: False for name in BOOLEAN_TRIGGER_VARIABLES}
    context["always"] = True

    for key, value in profile.items():
        if key != "ai_type":
            context[key] = _to_bool(value)

    for key, value in state.items():
        if key in {"profile", "ai_type", "target"}:
            continue
        if isinstance(value, (dict, list, set, tuple)):
            continue
        context[key] = _to_bool(value)

    gdpr_mandatory = state.get("gdpr_mandatory")
    if gdpr_mandatory is None:
        gdpr_mandatory = (state.get("gdpr_status") or "mandatory") == "mandatory"
    context["gdpr_mandatory"] = _to_bool(gdpr_mandatory)

    ai_type = _s(state.get("ai_type") or state.get("target"), "system").lower()
    context["ai_type"] = ai_type

    # Бизнес-инвариант: продуктовые риски не применяются к независимой модели.
    if ai_type == "model":
        for flag in PRODUCT_RISK_FLAGS:
            context[flag] = False

    return context


def _normalize_trigger_expression(trigger: str) -> str:
    """Привести табличные AND/OR/NOT/TRUE/FALSE к Python-выражению."""
    expression = trigger.strip()
    replacements = {
        "AND": "and",
        "OR": "or",
        "NOT": "not",
        "TRUE": "True",
        "FALSE": "False",
    }
    for source, target in replacements.items():
        expression = re.sub(rf"\b{source}\b", target, expression, flags=re.IGNORECASE)
    return expression


def _validate_trigger_expression(tree: ast.AST, context: dict) -> None:
    """Запретить любые AST-узлы кроме boolean/string-сравнений."""
    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_TRIGGER_AST_NODES):
            raise ValueError(f"Unsupported trigger expression node: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id not in context:
            raise ValueError(f"Unknown trigger variable: {node.id}")
        if isinstance(node, ast.Compare) and len(node.ops) != 1:
            raise ValueError("Chained comparisons are not supported in Trigger_Variable")
        if isinstance(node, ast.Constant) and not isinstance(node.value, (bool, str)):
            raise ValueError("Only boolean and string constants are supported in Trigger_Variable")


def _initialize_missing_trigger_names(tree: ast.AST, context: dict) -> None:
    """Добавить отсутствующие переменные из выражения в контекст как False."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id not in context:
            context[node.id] = False


def _is_trigger_matched(trigger: str, state: dict, profile: dict) -> bool:
    """Проверить Trigger_Variable: одиночный ключ или сложное boolean-выражение."""
    normalized_trigger = trigger.strip()
    if not normalized_trigger or normalized_trigger.lower() == "always":
        return True

    context = _build_trigger_context(state, profile)
    expression = _normalize_trigger_expression(normalized_trigger)

    try:
        tree = ast.parse(expression, mode="eval")
        _initialize_missing_trigger_names(tree, context)
        _validate_trigger_expression(tree, context)
        return bool(eval(compile(tree, "<trigger_variable>", "eval"), {"__builtins__": {}}, context))
    except Exception:
        return False


def _is_role_shift_item(item: dict) -> bool:
    """Найти строку чек-листа про правовой статус сторон / Provider."""
    text = " ".join([
        item.get("id", ""),
        item.get("sheet", ""),
        item.get("requirement", ""),
        item.get("detailed_hint", ""),
    ]).lower()
    return any(marker in text for marker in ROLE_SHIFT_MARKERS)


def _with_role_shift_warning(item: dict) -> dict:
    """Вернуть копию задачи с динамическим предупреждением о role shift."""
    detailed_hint = item.get("detailed_hint", "")
    if ROLE_SHIFT_WARNING.strip() in detailed_hint:
        return item

    updated = item.copy()
    updated["detailed_hint"] = f"{detailed_hint}{ROLE_SHIFT_WARNING}" if detailed_hint else ROLE_SHIFT_WARNING.strip()
    return updated


def _append_role_shift_item(items: list[dict], all_items: list[dict]) -> list[dict]:
    """Принудительно добавить задачу о смене правового статуса, если она есть в CSV."""
    result = []
    role_shift_added = False

    for item in items:
        if _is_role_shift_item(item):
            result.append(_with_role_shift_warning(item))
            role_shift_added = True
        else:
            result.append(item)

    if role_shift_added:
        return result

    for item in all_items:
        if _is_role_shift_item(item):
            result.append(_with_role_shift_warning(item))
            break

    return result


def filter_content_by_state(state: dict) -> list[dict]:
    """
    Фильтрует меры по полной сессии пользователя.

    ai_type="model" включает только модельные/GPAI требования и игнорирует продуктовые риски.
    ai_type="system" включает продуктовые риски и rule shift по ст. 25 AI Act.
    """
    all_items = load_content_checklist()
    profile = state.get("profile", {})
    ai_type = state.get("ai_type") or state.get("target")
    result = []

    for item in all_items:
        trigger = item.get("trigger_variable", "always").strip()

        if _is_trigger_matched(trigger, state, profile):
            result.append(item)

    if ai_type == "system" and (profile.get("is_modifier") or profile.get("is_brand_owner")):
        result = _append_role_shift_item(result, all_items)

    return result


def filter_content_by_profile(profile: dict, gdpr_status: str) -> list[dict]:
    """
    Фильтрует меры по профилю пользователя и GDPR статусу.
    
    profile: {"is_gen_ai": bool, "is_child": bool, "has_scraping": bool, "is_high_risk": bool}
    gdpr_status: "anonymous" | "mandatory"
    """
    return filter_content_by_state({
        "profile": profile,
        "gdpr_status": gdpr_status,
        "gdpr_mandatory": gdpr_status == "mandatory",
    })


# === Gemini_KB (Фаза 3, для будущего использования) ===
def load_gemini_kb() -> dict[str, str]:
    """
    Загружает базу знаний для Gemini.
    Возвращает: {"Retraining": "Описание...", "DPIA": "Методология...", ...}
    """
    url = _get_url("CSV_URL_GEMINI_KB", DEFAULT_CSV_GEMINI_KB)
    try:
        rows = _fetch_csv(url)
        result = {}
        for row in rows:
            topic = _s(row.get("Topic") or row.get("Тема"))
            context = _s(row.get("Context_Data (Текст для промпта)") or row.get("Context_Data") or row.get("Текст для промпта"))
            if topic:
                result[topic] = context
        return result
    except Exception:
        return {
            "Retraining": "Описание стратегий переобучения модели при отзыве согласия пользователя.",
            "DPIA": "Методология оценки рисков для ИИ-проектов по стандартам CNIL.",
            "De-anon": "Техническое описание атак (Inversion, Extraction) для проверки весов.",
            "AI_Act": "Справка по классификации систем высокого риска и требованиям к ним.",
        }
