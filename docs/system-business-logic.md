# AI GDPR Navigator: Business Logic Specification

This document is the canonical business-logic reference for the bot. Update it when changing FSM routes, Google Sheets columns, session fields, checklist filtering, or report content.

## Runtime Flow

1. `/start` asks whether the user already knows if GDPR applies.
2. Unknown GDPR status starts the GDPR qualification graph, Block L.
3. Every terminal result of Block L now routes into Block M, AI Act screening.
4. Block M captures the AI Act target and EU-market scope.
5. If the scenario continues, the bot asks System_Triggers profile questions.
6. The checklist is filtered from Content_Checklist.
7. The report summarizes the session, skipped measures, GDPR status, AI Act status, and legal comments.

## Session Fields

Core FSM fields:

- `state`: current FSM state.
- `logic_node`: current Block L node, starting from `L1`.
- `ai_act_node`: current Block M node, starting from `M1`.
- `trigger_index`: current System_Triggers question index.
- `content_items`, `content_index`, `content_done`, `content_skipped`: checklist progress.
- `prohibited_items`: prohibited AI practices selected or inferred from the `prohibited_type` trigger.

Legal and routing fields:

- `gdpr_status`: `"anonymous"` or `"mandatory"`.
- `gdpr_mandatory`: `True` when GDPR obligations must be shown.
- `attack_risk`: `True` when the user did not run extraction-attack tests in `L3`.
- `target`: `"system"` for a finished AI system/application, `"model"` for an independent AI model.
- `ai_act_status`: `"in_scope"` or `"AIA_OUT_OF_SCOPE"`.

Profile fields from System_Triggers:

- `is_gen_ai`
- `prohibited_type`
- `is_child`
- `has_scraping`
- `is_high_risk`
- `is_creator`
- `is_brand_owner`
- `is_modifier`

## Block L: GDPR Qualification

| ID | Question | Yes | No |
| --- | --- | --- | --- |
| `L1` | Содержит ли датасет персональные данные (ПД)? | `L2` | `M1`; `gdpr_status = "anonymous"`, `gdpr_mandatory = False` |
| `L2` | Модель создана для поиска/выдачи инфо о лицах? | `M1`; `gdpr_status = "mandatory"`, `gdpr_mandatory = True` | `L3` |
| `L3` | Проводились ли атаки на извлечение ПД из весов? | `L4` | `M1`; `gdpr_status = "mandatory"`, `gdpr_mandatory = True`, `attack_risk = True` |
| `L4` | Риск ре-идентификации признан ничтожным? | `M1`; `gdpr_status = "anonymous"`, `gdpr_mandatory = False` | `M1`; `gdpr_status = "mandatory"`, `gdpr_mandatory = True` |

Google Sheets may also return a combined transition value. The parser must accept these forms:

- `M1 (Флаг: gdpr=True) EXIT_GDPR` -> route to `M1`; `gdpr_mandatory = True`.
- `M1 (Флаг: gdpr=False) EXIT_ANON` -> route to `M1`; `gdpr_mandatory = False`.

When `gdpr=True/False` is present, this explicit flag is the source of truth for `gdpr_mandatory`. Any `EXIT_*` text in the same cell is a human note only and must not drive routing or flags.

## Block M: AI Act Screening

Question text for `M1` and `M2` is loaded from the last two rows of the `Logic_GDPR` sheet, after `L1-L4`.

`M1`: «Что именно мы тестируем: независимую ИИ-модель или готовое приложение/систему, куда этот ИИ встроен?»

- Система / Yes -> `M2`; `target = "system"`.
- Модель / No -> `M2`; `target = "model"`.

`M2`: «Связан ли ваш ИИ-продукт с рынком Европейского союза (ЕС)?»

- Yes -> first System_Triggers question; `ai_act_status = "in_scope"`.
- No -> `ai_act_status = "AIA_OUT_OF_SCOPE"`.

If `M2 = No` and `gdpr_mandatory = True`, the bot must notify the user:

«Ваш продукт не связан с рынком Европейского союза, поэтому специфические требования по AI Act на него не распространяются, но тк есть ПД европейских пользователей, то бот переходит к вашим обязательствам по GDPR».

Then it continues to System_Triggers and the GDPR checklist.

If `M2 = No` and `gdpr_mandatory = False`, the bot may stop the session because both GDPR mandatory obligations and AI Act scope are absent.

## System_Triggers Profile

These questions are loaded from the `System_Triggers` Google Sheet and stored in `state["profile"]`.

| Variable | Meaning |
| --- | --- |
| `is_gen_ai` | Generative AI behavior: text, images, video, code, audio. |
| `prohibited_type` | The system uses AI practices prohibited by Article 5 AI Act. |
| `is_child` | Product is aimed at users under 18. |
| `has_scraping` | Data was collected by web scraping. |
| `is_high_risk` | Potentially high-risk domain such as HR, medicine, education, biometrics, justice. |

If `prohibited_type = True`, the bot must stop the flow before checklist generation and send one visually prominent warning:

«🛑 КРИТИЧЕСКИЙ СТАТУС: ЗАПРЕЩЕНО В ЕС (PROHIBITED AI)
Ваш продукт использует практики, которые полностью запрещены ст. 5 AI Act. Вывод этой системы на рынок Европы или её использование может повлечь за собой немедленный бан продукта и оборотные штрафы до 35 000 000 € (или 7% от мирового годового оборота компании).
Причина блокировки: Ваш ИИ использует функции: [selected prohibited practices].
⚙Что делать дальше? Комплаенс-отчет заблокирован, так как эти функции невозможно «настроить» легально. Вам необходимо:
1. Удалить/вырезать запрещенный функционал из архитектуры системы.
2. Ввести геоблокировку (Geo-fencing), если вы хотите оставить эти функции для рынков США или Азии, полностью закрыв доступ для пользователей и IP-адресов из Европейского союза.
После изменения бизнес-логики вы можете пройти тест заново.»

The warning must not include a checklist/report button. `prohibited_items` should be populated from option labels in `System_Triggers` when available; if the sheet only has the current Yes/No question, the bot may use the default Article 5 practice labels as the reason text.

## Checklist Filtering

Content comes from `Content_Checklist`.

Include an item when:

- `Trigger_Variable = "always"`.
- `Trigger_Variable` matches a truthy profile flag.
- `Trigger_Variable = "gdpr_mandatory"` and `gdpr_mandatory = True`.

Use `gdpr_status` only as a backward-compatible representation of the legal status. New business logic should prefer `gdpr_mandatory`.

## Mandatory Anonymous Disclaimer

For every user-facing result or hint path where `gdpr_mandatory = False`, include this legal disclaimer:

«Документация должна позволять регуляторам и пользователям убедиться, что модель не обрабатывает персональные данные».

This applies to:

- the post-Block-L / pre-Block-M message;
- the `AIA_OUT_OF_SCOPE` terminal message when GDPR is not mandatory;
- final report comments and documentation guidance.

## Google Sheets Contract

The bot currently reads four published CSV tabs:

- `Logic_GDPR`: Block L graph and Block M question text in rows `M1` and `M2`.
- `Content_Checklist`: checklist measures and trigger variables.
- `System_Triggers`: profile questions.
- `Gemini_KB`: future expert knowledge base.

When Google Sheets changes, update `structure-sheets.txt` and this document in the same change.
