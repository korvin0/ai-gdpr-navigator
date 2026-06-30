"""In-memory FSM state для сессий пользователей."""

# === FSM States ===
STATE_LOGIC = 0      # Фаза 0: Логический квест GDPR
STATE_AI_ACT = 1     # Блок M: Скрининг AI Act
STATE_TRIGGERS = 2   # Фаза 1: Профилирование (триггеры)
STATE_CHECKLIST = 3  # Фаза 2: Чек-лист мер
STATE_REPORT = 4     # Фаза 3: Отчет
STATE_REVIEW = 5     # Ожидание текста отзыва
STATE_BLOCKED = 6    # Терминальный стоп из-за prohibited AI

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
            "is_gen_ai": False,
            "prohibited_type": False,
            "is_prohibited": False,
            "is_child": False,
            "has_scraping": False,
            "is_high_risk": False,
            "is_creator": False,
            "is_brand_owner": False,
            "is_modifier": False,
        },
        "prohibited_items": [],
        "gdpr_status": None,
        "gdpr_mandatory": None,
        "attack_risk": False,
        "ai_type": None,
        "target": None,
        "ai_act_status": None,
        "global_status": None,
        "anon_documentation_disclaimer": False,
        "ai_act_node": "M1",
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
