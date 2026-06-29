"""Регистрация routers обработчиков."""

from aiogram import Dispatcher, Router

from . import ai_act, checklist, logic, report, start, triggers

ROUTERS: list[Router] = [
    start.router,
    logic.router,
    ai_act.router,
    triggers.router,
    checklist.router,
    report.router,  # текстовый handler отзывов — последним
]


def setup_routers(dp: Dispatcher) -> None:
    """Подключить все routers к диспетчеру."""
    for router in ROUTERS:
        dp.include_router(router)
