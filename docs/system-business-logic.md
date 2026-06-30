# AI GDPR Navigator: Business Logic Specification

This document is the canonical business-logic reference for the bot. Update it when changing FSM routes, Google Sheets columns, session fields, checklist filtering, or report content.

## Runtime Flow

1. `/start` asks whether the user already knows if GDPR applies.
2. Unknown GDPR status starts the GDPR qualification graph, Block L.
3. Every terminal result of Block L now routes into Block M, AI Act screening.
4. Block M captures `ai_type` and EU-market scope.
5. The bot asks System_Triggers profile questions only after `M2 = Yes`.
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
- `ai_type`: `"system"` for a finished AI system/application, `"model"` for an independent AI model.
- `target`: backward-compatible alias for `ai_type`.
- `ai_act_status`: `"in_scope"`, `"AIA_OUT_OF_SCOPE"`, or `"PROHIBITED_RISK"`.
- `global_status`: terminal global status such as `"PROHIBITED_RISK"`.
- `anon_documentation_disclaimer`: `True` only when the Block L route used `L4 / Yes`.

Profile fields from System_Triggers:

- `is_gen_ai`
- `prohibited_type`
- `is_prohibited`
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

- `📦 Независимая модель` -> `M2`; `ai_type = "model"`.
- `🖥 Готовая система` -> `M2`; `ai_type = "system"`.

`M2`: «Связан ли ваш ИИ-продукт с рынком Европейского союза (ЕС)?»

- Yes -> first System_Triggers question; `ai_act_status = "in_scope"`.
- No -> `ai_act_status = "AIA_OUT_OF_SCOPE"`; AI Act questionnaire stops. If `gdpr_mandatory = True`, the bot skips System_Triggers, filters `Content_Checklist` with the current session context, and starts the normal checklist flow for the applicable measures. If `gdpr_mandatory = False`, the bot stops without checklist because both AI Act and mandatory GDPR obligations are out of scope.

## System_Triggers Profile

These questions are loaded from the `System_Triggers` Google Sheet and stored in `state["profile"]`.

| Variable | Meaning |
| --- | --- |
| `is_gen_ai` | Generative AI behavior: text, images, video, code, audio. |
| `prohibited_type` / `is_prohibited` | The system uses AI practices prohibited by Article 5 AI Act. |
| `is_child` | Product is aimed at users under 18. |
| `has_scraping` | Data was collected by web scraping. |
| `is_high_risk` | Potentially high-risk domain such as HR, medicine, education, biometrics, justice. |

If `prohibited_type = True`, the bot must set `ai_act_status = "PROHIBITED_RISK"` and `global_status = "PROHIBITED_RISK"`, stop the flow before checklist generation, and send one visually prominent warning:

«🛑 КРИТИЧЕСКИЙ СТАТУС: ЗАПРЕЩЕНО В ЕС (PROHIBITED AI)
Ваш продукт использует практики, которые полностью запрещены ст. 5 AI Act. Вывод этой системы на рынок Европы или её использование может повлечь за собой немедленный бан продукта и оборотные штрафы до 35 000 000 € (или 7% от мирового годового оборота компании).
Причина блокировки: Ваш ИИ использует функции: [selected prohibited practices].
⚙Что делать дальше? Комплаенс-отчет заблокирован, так как эти функции невозможно «настроить» легально. Вам необходимо:
1. Удалить/вырезать запрещенный функционал из архитектуры системы.
2. Ввести геоблокировку (Geo-fencing), если вы хотите оставить эти функции для рынков США или Азии, полностью закрыв доступ для пользователей и IP-адресов из Европейского союза.
После изменения бизнес-логики вы можете пройти тест заново.»

The warning must not include a checklist/report button. `prohibited_items` should be populated from option labels in `System_Triggers` when available; if the sheet only has the current Yes/No question, the bot may use the default Article 5 practice labels as the reason text.

## Report Generation Scenarios

`AIA_OUT_OF_SCOPE`:

- The report profile role must read: `Вне зоны регулирования AI Act (опрос не проводился)`.
- The AI Act category must read: `Не применимо (Out of Scope)`.
- Statistics are calculated only from the already filtered `Content_Checklist` rows whose `Trigger_Variable` matched the current session.
- Recommended next steps must use GDPR actions unless high-risk or child flags require otherwise. Do not show AI Act regulatory actions for an out-of-scope project.

`PROHIBITED_RISK` / `is_prohibited = True`:

- The AI Act category must read: `🔴 Запрещенная практика (Prohibited - ст. 5 AI Act)`.
- Standard technical/product task lists and next regulatory steps are cleared.
- The comment block must be the hard Article 5 legal warning.

High-risk or GPAI:

- If `is_high_risk = True`, the AI Act category must read `🔥 Высокий риск (High-Risk System)`.
- If `is_gen_ai = True`, the AI Act category must read `🤖 Модель общего назначения (General Purpose AI / GPAI)` when high-risk is absent.
- For legal in-scope high-risk or GPAI systems, recommended next steps must include technical documentation for an EU notified body, conformity assessment, and registration in the EU AI database.

## Checklist Filtering

Content comes from `Content_Checklist`.

Include an item when:

- `Trigger_Variable = "always"`.
- `Trigger_Variable` matches a truthy profile flag.
- `Trigger_Variable = "gdpr_mandatory"` and `gdpr_mandatory = True`.
- `Trigger_Variable` is a boolean expression over session variables, for example `gdpr_mandatory AND (is_creator OR is_modifier)` or `ai_type == 'system' AND is_high_risk`.

Use `gdpr_status` only as a backward-compatible representation of the legal status. New business logic should prefer `gdpr_mandatory`.

Before evaluating `Trigger_Variable`, the reducer must build a typed context:

- Boolean variables from `state["profile"]` and session fields are normalized to real `True`/`False` values.
- Missing variables referenced by a checklist expression are added to the context as `False`.
- `gdpr_mandatory` comes from the Block L result in Phase 0, with `gdpr_status` used only as a fallback.
- `ai_type` remains a string and is compared as `"system"` or `"model"`.

`ai_type` is a super-trigger for the checklist reducer:

- If `ai_type = "model"`, product risk flags `is_high_risk`, `is_child`, and `prohibited_type` are masked to `False` for checklist evaluation. Model/GPAI requirements should be expressed in CSV with conditions such as `ai_type == 'model' AND is_gen_ai`.
- If `ai_type = "system"`, evaluate full product risks including `is_high_risk`, `is_child`, and `prohibited_type`.
- If `ai_type = "system"` and either `is_modifier = True` or `is_brand_owner = True`, force-add the checklist row about legal status of parties / Controller vs Processor / Provider. Append the Article 25 role-shift warning to that row's `Detailed_Hint`.

## Checklist UI Text

Checklist summary and per-item headings must not hard-code GDPR:

- If both `gdpr_mandatory = True` and AI Act risk triggers (`is_high_risk` or `is_gen_ai`) are active, the summary text must mention GDPR and AI Act and use the audit CTA.
- If only `gdpr_mandatory = True`, the summary text must mention GDPR/privacy requirements and use the GDPR CTA.
- If `ai_act_status = "AIA_OUT_OF_SCOPE"` or `AIA_OUT_OF_SCOPE = True`, per-item headings must always say GDPR and must not mention AI Act, regardless of `Trigger_Variable`.
- Per-item headings are derived from the row's `Trigger_Variable`: GDPR for `gdpr_mandatory`, AI Act for `is_high_risk`/`is_gen_ai`/AI Act role triggers, and `GDPR & AI Act` when both kinds of variables appear in the same condition.

## Mandatory Anonymous Disclaimer

The hidden L4 documentation disclaimer is included in the final report only when `L4 / Yes` was the source route and therefore `gdpr_mandatory = False`:

«Документация должна позволять регуляторам и пользователям убедиться, что модель не обрабатывает персональные данные».

Other anonymous/GDPR-not-mandatory messages may explain the status, but the final generator must use `anon_documentation_disclaimer` rather than every `gdpr_mandatory = False` case.

## Google Sheets Contract

The bot currently reads four published CSV tabs:

- `Logic_GDPR`: Block L graph and Block M question text in rows `M1` and `M2`.
- `Content_Checklist`: checklist measures and trigger variables.
- `System_Triggers`: profile questions.
- `Gemini_KB`: future expert knowledge base.

When Google Sheets changes, update `structure-sheets.txt` and this document in the same change.

## Reset

`/start`, `/cancel`, and the report restart button must call `reset_state()` so all screening variables return to their initial `False`/`None` values and old answers cannot leak into the new audit.
