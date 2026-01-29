#!/usr/bin/env python3
"""
Точка входа: запуск телеграм-бота с фазами 0–3 и чтением Google Sheets.
"""
import asyncio
import os

from dotenv import load_dotenv

from src.bot import run_polling

load_dotenv()


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
