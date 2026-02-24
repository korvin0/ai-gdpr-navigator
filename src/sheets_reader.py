"""
Чтение 4 вкладок Google Sheets: Logic_GDPR, Content_Checklist, System_Triggers, Gemini_KB.
Использует опубликованные CSV URL (Файл -> Опубликовать в интернете -> CSV).
"""
import csv
import os
from typing import Optional
from urllib.request import urlopen

# === CSV URLs для каждой вкладки ===
DEFAULT_CSV_LOGIC_GDPR = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=2046117556&single=true&output=csv"
DEFAULT_CSV_CONTENT_CHECKLIST = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=1062279979&single=true&output=csv"
DEFAULT_CSV_SYSTEM_TRIGGERS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=1004258855&single=true&output=csv"
DEFAULT_CSV_GEMINI_KB = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQMyZ-KFD_AJgQNpk-Q0j6A5viEN6JFlRMbAwkFCMASEHvFAUsXIV61D-WC_13guegJAIlo6gSF5z6Y/pub?gid=1940152089&single=true&output=csv"


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


# === System_Triggers (Фаза 0) ===
def load_system_triggers() -> list[dict]:
    """
    Загружает триггеры для Фазы 0.
    Возвращает: [{"variable": "is_gen_ai", "question_text": "...", "ui_type": "Yes/No Buttons", "hint": "..."}, ...]
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
            if not hint:
                for k, v in row.items():
                    if "Hint" in k or "Подсказка" in k:
                        hint = _s(v)
                        if hint:
                            break
            if variable and question:
                result.append({
                    "variable": variable,
                    "question_text": question,
                    "ui_type": ui_type,
                    "hint": hint,
                })
        return result
    except Exception:
        # Fallback данные
        return [
            {"variable": "is_gen_ai", "question_text": "Это Генеративный ИИ (текст, изображения, видео)?", "ui_type": "Yes/No Buttons", "hint": "Генеративный ИИ создаёт новый контент (текст, изображения, видео) на основе обучающих данных."},
            {"variable": "is_child", "question_text": "Проект ориентирован на детей до 18 лет?", "ui_type": "Yes/No Buttons", "hint": "Если среди пользователей могут быть несовершеннолетние, применяются усиленные меры защиты."},
            {"variable": "has_scraping", "question_text": "Вы используете веб-скрейпинг для сбора данных?", "ui_type": "Yes/No Buttons", "hint": "Веб-скрейпинг — автоматический сбор данных с сайтов. Требует проверки прав и robots.txt."},
            {"variable": "is_high_risk", "question_text": "ИИ используется в критической сфере (HR, медицина)?", "ui_type": "Yes/No Buttons", "hint": "Системы высокого риска по AI Act: HR, медицина, правосудие, образование, биометрия."},
        ]


# === Logic_GDPR (Фаза 1) ===
def load_logic_gdpr() -> list[dict]:
    """
    Загружает логику квеста для Фазы 1.
    Возвращает: [{"id": "L1", "question": "...", "hint": "...", "next_yes": "L2", "next_no": "EXIT_ANON"}, ...]
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
            {"id": "L1", "question": "Содержит ли датасет персональные данные (ПД)?", "hint": "ПД — любая инфо о человеке (email, ID, фото, скрейпинг).", "next_yes": "L2", "next_no": "EXIT_ANON"},
            {"id": "L2", "question": "Модель создана для поиска/выдачи инфо о лицах?", "hint": "Например: распознавание лиц или генерация досье.", "next_yes": "EXIT_GDPR", "next_no": "L3"},
            {"id": "L3", "question": "Проводились ли атаки на извлечение ПД из весов?", "hint": "Проверка, можно ли \"вытащить\" данные через API модели.", "next_yes": "L4", "next_no": "WARN_ATTACK"},
            {"id": "L4", "question": "Риск ре-идентификации признан ничтожным?", "hint": "Если вероятность восстановления ПД из модели близка к 0.", "next_yes": "EXIT_ANON", "next_no": "EXIT_GDPR"},
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
                    "trigger_variable": trigger_var.lower().strip(),
                    "detailed_hint": detailed_hint,
                })
        return result
    except Exception:
        # Fallback данные
        return [
            {"id": "1.1", "sheet": "Блок А", "requirement": "Определить роль: Контроллер или Процессор.", "trigger_variable": "always", "detailed_hint": "См. Лист 2: Определите, кто несет ответственность."},
            {"id": "10.1", "sheet": "Блок Г", "requirement": "Использовать формат весов safetensors.", "trigger_variable": "is_gen_ai", "detailed_hint": "Защита от выполнения произвольного кода."},
        ]


def filter_content_by_profile(profile: dict, gdpr_status: str) -> list[dict]:
    """
    Фильтрует меры по профилю пользователя и GDPR статусу.
    
    profile: {"is_gen_ai": bool, "is_child": bool, "has_scraping": bool, "is_high_risk": bool}
    gdpr_status: "anonymous" | "mandatory"
    """
    all_items = load_content_checklist()
    result = []
    
    for item in all_items:
        trigger = item.get("trigger_variable", "always").lower().strip()
        
        # always - всегда показываем
        if trigger == "always":
            result.append(item)
        # Триггеры из профиля
        elif trigger == "is_gen_ai" and profile.get("is_gen_ai"):
            result.append(item)
        elif trigger == "is_child" and profile.get("is_child"):
            result.append(item)
        elif trigger == "has_scraping" and profile.get("has_scraping"):
            result.append(item)
        elif trigger == "is_high_risk" and profile.get("is_high_risk"):
            result.append(item)
        # GDPR mandatory
        elif trigger == "gdpr_mandatory" and gdpr_status == "mandatory":
            result.append(item)
    
    return result


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
