"""Сохранение отзывов пользователей."""

import os

REVIEWS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reviews.txt")


def save_review(username: str, review_text: str, date_str: str) -> None:
    """Записать отзыв в файл."""
    with open(REVIEWS_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{date_str}] @{username}: {review_text}\n")
