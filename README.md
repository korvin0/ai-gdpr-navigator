# AI GDPR Navigator

Telegram-бот на aiogram для проверки ИИ-проектов на соответствие GDPR и AI Act. Читает данные из Google Sheets (опубликованный CSV), ведёт пользователя через интерактивный аудит и генерирует финальный отчет.

## Архитектура

```
/start
   │
   ▼
Фаза 0: GDPR-квалификация (Block L)
   │  → gdpr_mandatory, attack_risk
   ▼
Block M: Скрининг AI Act
   │  → target, ai_act_status
   ▼
Фаза 1: Профилирование (System_Triggers)
   │  → is_gen_ai, prohibited_type, is_child, has_scraping, is_high_risk
   │  → при prohibited_type = Yes аудит блокируется как Prohibited AI
   ▼
Фаза 2: Персональный чек-лист мер
   │  → Фильтрация по профилю, gdpr_mandatory и AI Act scope
   │  → Кнопки: Сделано / Инфо / Пропустить
   ▼
Фаза 3: Финальный отчет
      → Статистика, юридический комментарий
      → Кнопка "Спросить Gemini" (в разработке)
```

## Фазы

- **Фаза 0** — Квалификация GDPR и AI Act: Block L определяет `gdpr_mandatory`, затем Block M определяет `target` и `ai_act_status`.
- **Фаза 1** — Профилирование: вопросы о типе ИИ, запрещенных AI Act практиках, аудитории, источнике данных и уровне риска. Ответ `Yes` на `prohibited_type` останавливает аудит до чек-листа и отчета.
- **Фаза 2** — Чек-лист мер: персонализированный список требований с подсказками из Google Sheets.
- **Фаза 3** — Отчет: итоговый документ с рекомендациями и юридическим комментарием.

Подробная бизнес-логика описана в `docs/system-business-logic.md`.

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
├── docs/                # Каноническая бизнес-спецификация
├── .cursor/rules/       # Правила для Cursor AI
└── *.txt                # Спецификации фаз и шаблоны
```

## Структура Google Sheets

### Logic_GDPR
| ID | Question (Вопрос) | Hint | Next_If_Yes | Next_If_No |
|----|-------------------|------|-------------|------------|
| L1 | Вопрос... | Подсказка... | L2 | M1 |
| M1 | Вопрос AI Act... | | M2 | M2 |

В этой же вкладке после `L1-L4` должны лежать строки `M1` и `M2`: бот читает из них тексты вопросов AI Act Screening. Старые значения `EXIT_ANON`, `EXIT_GDPR`, `WARN_ATTACK` могут оставаться в таблице как человеческие пометки, но код не использует их для маршрутизации или установки флагов.

### Content_Checklist
| ID | Sheet | Requirement (Требование) | Trigger_Variable | Detailed_Hint |
|----|-------|--------------------------|------------------|---------------|
| 1.1 | Блок А | Требование... | always | Подсказка... |

### System_Triggers
| Variable | Question_Text | UI_Type | Options |
|----------|---------------|---------|---------|
| is_gen_ai | Вопрос... | Yes/No Buttons | |
| prohibited_type | Вопрос о практиках, запрещенных ст. 5 AI Act | Yes/No Buttons | Опциональный список практик для причины блокировки |

### Gemini_KB
| Topic | Context_Data |
|-------|--------------|
| DPIA | Описание... |

## Команды бота

- `/start` — начать новый аудит
- `/cancel` — сбросить и начать заново

## Gemini AI (в разработке)

Кнопка "Спросить Gemini" присутствует в Фазе 3, но пока показывает заглушку. В будущей версии будет подключен Gemini API для консультаций по результатам аудита.
