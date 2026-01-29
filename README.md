# AI GDPR Navigator

Telegram-бот на aiogram для проверки ИИ-проектов на соответствие GDPR и AI Act. Читает данные из Google Sheets (опубликованный CSV), ведёт пользователя через интерактивный аудит и генерирует финальный отчет.

## Архитектура

```
/start
   │
   ▼
Фаза 0: Профилирование (4 вопроса Yes/No)
   │  → is_gen_ai, is_child, has_scraping, is_high_risk
   ▼
Фаза 1: Логический квест GDPR
   │  → L1 → L2 → L3 → L4 → EXIT_ANON | EXIT_GDPR | WARN_ATTACK
   ▼
Фаза 2: Персональный чек-лист мер
   │  → Фильтрация по профилю и статусу GDPR
   │  → Кнопки: Сделано / Инфо / Пропустить
   ▼
Фаза 3: Финальный отчет
      → Статистика, юридический комментарий
      → Кнопка "Спросить Gemini" (в разработке)
```

## Фазы

- **Фаза 0** — Профилирование: 4 вопроса о типе ИИ, аудитории, источнике данных и уровне риска.
- **Фаза 1** — Квалификация GDPR: логический квест для определения статуса (Anonymous / Mandatory).
- **Фаза 2** — Чек-лист мер: персонализированный список требований с подсказками из Google Sheets.
- **Фаза 3** — Отчет: итоговый документ с рекомендациями и юридическим комментарием.

## Установка и запуск

```bash
# Активировать venv
source venv/bin/activate   # Linux/macOS
# или: venv\Scripts\activate  # Windows

# Установить зависимости (если нужно)
pip install -r requirements.txt

# Скопировать и настроить .env
cp env.example .env
# Отредактировать .env: добавить TELEGRAM_BOT_TOKEN

# Запустить
python main.py
```

### Токен Telegram

1. Получить токен у [@BotFather](https://t.me/BotFather)
2. Добавить в `.env`:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен
   ```

### Google Sheets

По умолчанию бот использует встроенные CSV URL — ничего настраивать не нужно.

Для использования своих таблиц:
1. Создайте Google Sheet с 4 вкладками: `Logic_GDPR`, `Content_Checklist`, `System_Triggers`, `Gemini_KB`
2. Опубликуйте каждую вкладку: **Файл → Опубликовать в интернете → выбрать лист → CSV**
3. Добавьте URL в `.env`:
   ```
   CSV_URL_LOGIC_GDPR=https://docs.google.com/...?gid=...&output=csv
   CSV_URL_CONTENT_CHECKLIST=https://docs.google.com/...?gid=...&output=csv
   CSV_URL_SYSTEM_TRIGGERS=https://docs.google.com/...?gid=...&output=csv
   CSV_URL_GEMINI_KB=https://docs.google.com/...?gid=...&output=csv
   ```

## Структура проекта

```
├── main.py              # Точка входа
├── src/
│   ├── bot.py           # FSM, обработчики, генерация отчета
│   └── sheets_reader.py # Загрузка 4 вкладок из CSV
├── env.example          # Пример .env
├── requirements.txt     # Зависимости
└── *.txt                # Спецификации фаз и шаблоны
```

## Структура Google Sheets

### Logic_GDPR
| ID | Question (Вопрос) | Hint | Next_If_Yes | Next_If_No |
|----|-------------------|------|-------------|------------|
| L1 | Вопрос... | Подсказка... | L2 | EXIT_ANON |

### Content_Checklist
| ID | Sheet | Requirement (Требование) | Trigger_Variable | Detailed_Hint |
|----|-------|--------------------------|------------------|---------------|
| 1.1 | Блок А | Требование... | always | Подсказка... |

### System_Triggers
| Variable | Question_Text | UI_Type |
|----------|---------------|---------|
| is_gen_ai | Вопрос... | Yes/No Buttons |

### Gemini_KB
| Topic | Context_Data |
|-------|--------------|
| DPIA | Описание... |

## Команды бота

- `/start` — начать новый аудит
- `/cancel` — сбросить и начать заново

## Gemini AI (в разработке)

Кнопка "Спросить Gemini" присутствует в Фазе 3, но пока показывает заглушку. В будущей версии будет подключен Gemini API для консультаций по результатам аудита.
