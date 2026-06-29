"""Форматирование текста для Telegram MarkdownV2."""


def progress_block(phase: int) -> str:
    """Блок прогресса по этапам (MarkdownV2, уже экранирован)."""
    labels = [
        "Проверка применимости GDPR",
        "Определить профиль проекта \\(7 вопросов\\)",
        "Список мер для соответствия GDPR",
        "Получить отчет для разработчиков",
    ]
    lines = ["*Этапы проверки:*"]
    for i, label in enumerate(labels):
        if i < phase:
            lines.append(f"✅ ~{label} \\- сделано~")
        elif i == phase:
            lines.append(f"👉 {label}")
        else:
            lines.append(f"☑️ {label}")
    return "\n".join(lines)


def escape_md(text: str) -> str:
    """Экранировать специальные символы для MarkdownV2."""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
