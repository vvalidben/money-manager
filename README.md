# Money Manager

A local-first personal finance application for Windows, built with Python,
PySide6 and SQLite. Your financial data stays in a database on your computer;
nothing is sent anywhere unless you turn on online AI and confirm each request.

**Version 1.6.0.** It covers accounts, transactions (typed or imported from a
bank statement) and transfers between accounts, monthly budgets, allocations, a dashboard, statistics, goals,
subscriptions and bills, investment tracking, an optional AI advisor, settings,
category rules for imports, recurring entries, loans and debts, receipts, net worth over time, monthly and yearly PDF reports, a Windows Hello app lock, dark and light themes, a cash-flow forecast, reminders as Windows notifications, an English, French and Arabic interface, an optional update check, and backups (password-protected if you like, and automatic daily copies you can restore). See
[packaging/RELEASE_NOTES.md](packaging/RELEASE_NOTES.md) for the release notes.

**Contents:** [Requirements](#requirements) ·
[Installation](#installation) · [Running from source](#running-from-source) ·
[Building the executable](#building-the-executable) ·
[Configuration](#configuration) · [AI configuration](#ai-configuration) ·
[Database location](#database-location) · [Troubleshooting](#troubleshooting) ·
[Technical reference](#technical-reference)

## Requirements

**To use the application (release build):**

- Windows 10 or 11, 64-bit
- About 400 MB of free disk space (the program itself is about 200 MB)
- Nothing else: Python and every library are included.
- Optional, for AI:
  - Local AI: [Ollama](https://ollama.com).
  - Online AI: an Anthropic API key and an internet connection.

**To run from source or build:**

- Python 3.12 or newer (64-bit)
- The packages in `requirements.txt` (application) and `requirements-dev.txt`
  (tests and PyInstaller)

## Installation

**With the installer (recommended).** Download
`MoneyManager-1.6.0-Setup.exe` and run it. It installs Money Manager for you
only (no administrator rights) in `%LOCALAPPDATA%\Programs\MoneyManager`, adds
it to the Start menu (and, if you like, the desktop) and to Settings → Apps.
Running a newer Setup later updates it in place; your data is never touched.
To remove it: Settings → Apps → Installed apps → Money Manager → Uninstall
(your data is kept). Optionally check the download against the `.sha256` file:
`Get-FileHash .\MoneyManager-1.6.0-Setup.exe -Algorithm SHA256`.

**Or as a portable folder** (no installer at all):

1. Download `MoneyManager-1.6.0-windows-x64.zip`. Optionally, check it against
   the `.zip.sha256` file that comes with it:
   ```powershell
   Get-FileHash .\MoneyManager-1.6.0-windows-x64.zip -Algorithm SHA256
   ```
2. Extract it to a folder of your choice, for example
   `%LOCALAPPDATA%\Programs\MoneyManager` or `C:\Program Files\MoneyManager`.
   Keep the whole `MoneyManager` folder together, because `MoneyManager.exe`
   needs the `_internal` folder next to it.
3. Start `MoneyManager.exe`. You can pin it to Start or the taskbar, or create a
   shortcut to it.
4. The executable is not code-signed, so Windows SmartScreen may show
   *"Windows protected your PC"* the first time. Choose **More info → Run
   anyway**.

On first start the application creates its data folder
(`%LOCALAPPDATA%\MoneyManager`) and the database, then shows the dashboard.
Create an account to begin.

**Updating:** close the app and replace the program folder with the new
version. Your data is stored separately and is kept. If the new version changes
the database format, the database is upgraded automatically, and a backup copy
is made first.

**Uninstalling:** delete the program folder. Your data stays in
`%LOCALAPPDATA%\MoneyManager` until you delete that folder too. If you saved an
API key, remove it in Settings first, or delete `MoneyManager/anthropic_api_key`
in the Windows Credential Manager.

## Running from source

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"          # the application plus the test tools
python -m money_manager          # or: money-manager
```

`pip install -r requirements-dev.txt` installs the same dependencies without
installing the package. In that case, set `PYTHONPATH=src`.

**Tests.** The UI tests run headless (`tests/conftest.py` sets
`QT_QPA_PLATFORM=offscreen`), so no window opens:

```powershell
pytest
python -m coverage run --branch --source=src/money_manager -m pytest   # optional
python -m coverage report
```

Besides the unit and service tests, the suite contains:

| Test | What it proves |
|---|---|
| `tests/services/test_whole_app_fuzz.py` | Runs hundreds of random real operations: transactions and edits, transfers, archiving, goals, subscriptions, investments and backups. After every step, every service reports the same balance as an independent SQL sum, rejected operations change nothing, and the database passes its integrity checks. |
| `tests/services/test_statistics_crosscheck.py` | Recomputes the statistics and the financial analysis by brute force for presets, month ends, leap days and random ranges. |
| `tests/services/test_service_input_fuzz.py` | Calls every public service method with hostile values; only success or a clear validation error is allowed. |
| `tests/services/test_extreme_amounts.py` | Checks that the largest and smallest amounts stay exact through every feature. |
| `tests/ui/test_click_everything.py` | Clicks every button on every page, empty and with data, without an error. |
| `tests/ui/test_layout.py` | Checks that no page is wider than the smallest window. |
| `tests/test_architecture.py` | Enforces the layering rules (see *Project structure*). |

## Building the executable

```powershell
pip install -r requirements-dev.txt     # includes PyInstaller
python packaging\build.py               # or: powershell -ExecutionPolicy Bypass -File packaging\build.ps1
```

`packaging/build.py` runs these steps:

1. Deletes the old `build/` and `dist/` folders and stale `__pycache__`
   folders.
2. Runs PyInstaller with `packaging/MoneyManager.spec`. This is a one-folder
   windowed build. It includes the icon and version information, bundles the
   UI assets and the database migration scripts, and excludes the test tools.
3. Copies `README.md`, `RELEASE_NOTES.md` and `MoneyManager.example.ini` next
   to the executable.
4. **Tests the packaged executable** by running `MoneyManager.exe --self-test`
   twice, headless, in a temporary folder (never your real data or saved
   keys):
   - **First run:** creates the database and enters an account, transactions,
     an allocation with a transfer and a tagged expense, a goal, a
     subscription, an investment and AI settings. It then exports a backup and
     a CSV file.
   - **Restart:** checks that all of it persisted with the exact expected
     balances.
   - **Both runs:** check the dashboard and statistics figures and open every
     page.

   If any check fails, the build fails.
5. Creates `release/MoneyManager-<version>-windows-x64.zip` and a SHA-256
   checksum file.

Output:

- `dist\MoneyManager\MoneyManager.exe`, together with its `_internal` folder
- `release\MoneyManager-1.6.0-windows-x64.zip`

`--skip-self-test` skips step 4, which is not recommended. The application icon
is generated by `packaging/make_icon.py`, which needs Pillow and is only
required if you change the icon. The version number comes from
`src/money_manager/__init__.py`.

You can run the self-test on any build yourself. It writes `report.json` and
screenshots of every page into the folder you give it:

```powershell
dist\MoneyManager\MoneyManager.exe --self-test C:\Temp\mm-check
```

## Configuration

No configuration is required. Settings are read in this order, and the first
one found wins:

1. **Environment variables**
2. **A configuration file** `MoneyManager.ini`. The app uses the file named by
   `MONEY_MANAGER_CONFIG` if that is set. Otherwise it looks next to
   `MoneyManager.exe` (release build only).
3. **Defaults**

| Setting | Environment variable | INI key | Default |
|---|---|---|---|
| Data folder (database, logs, safety backups) | `MONEY_MANAGER_DATA_DIR` | `data_dir` | `%LOCALAPPDATA%\MoneyManager` |
| Log detail | `MONEY_MANAGER_LOG_LEVEL` | `log_level` | `INFO` (also `DEBUG`, `WARNING`, `ERROR`, `CRITICAL`) |
| Configuration file | `MONEY_MANAGER_CONFIG` | — | `MoneyManager.ini` next to the exe, if present |

Copy [packaging/MoneyManager.example.ini](packaging/MoneyManager.example.ini)
(it is also shipped next to the exe) to `MoneyManager.ini` and edit it:

```ini
[money_manager]
; A relative path is relative to this file, so "data" keeps everything
; inside the program folder (portable use, e.g. on a USB drive).
data_dir = data
log_level = INFO
```

Environment variables such as `%USERPROFILE%` are expanded. Unknown keys and
invalid values stop the app with a clear message instead of being ignored.
**Never put API keys in this file.** The currency, the AI provider and the
other preferences are stored in the database and changed on the Settings page.

## AI configuration

AI is **optional and off by default**. Every figure, chart and statistic is
calculated by the application itself. The AI only explains figures the app has
already calculated, and everything else works without it. Configure it in
**Settings → AI assistant**:

| Mode | What happens |
|---|---|
| **Off** (default) | No AI. The AI Advisor still shows the financial summary. |
| **Local** | Uses a model running in [Ollama](https://ollama.com) on this computer. Data never leaves the computer. |
| **Online** | Uses Anthropic's Claude API. Every request first shows exactly what will be sent and where, and nothing is sent until you tick the acknowledgement and click *Send*. |
| **Automatic** | Uses the local model when Ollama is running with it; otherwise uses online AI, which still needs your confirmation for each request. |

**Local AI (Ollama):**

1. Install Ollama and download a model, for example `ollama pull llama3.2`.
2. Make sure Ollama is running. Its default address is
   `http://localhost:11434`.
3. In Settings, choose *Local*, click *Find installed models*, pick one, then
   click *Test connection*.

Only addresses on this computer are accepted (`localhost`, `127.x`, `::1`).
Ollama *cloud* models are refused, because they run on Ollama's servers.

**Online AI (Anthropic):**

1. Create an API key in the [Anthropic Console](https://console.anthropic.com).
2. In Settings, choose *Online*, paste the key and save it. The key is stored
   in the **Windows Credential Manager** as `MoneyManager/anthropic_api_key`.
   It is never stored in the database, backups, logs, the INI file or the
   project.
   - As an alternative, set the environment variable `ANTHROPIC_API_KEY`. A
     key saved in Settings takes precedence.
3. Choose the model (default `claude-opus-5`), then click *Test connection*.
   The test does not send any financial data.

The release build already includes the Anthropic SDK. From source, install it
with `pip install -e ".[ai-online]"`.

**What online AI receives:** a summary of the figures the app has calculated
for the chosen period, such as totals, the savings rate, category changes and
trends, with category names. It never receives individual transactions,
transaction descriptions, or the names of accounts, goals, subscriptions or
investments. The consent dialog shows the exact text before anything is sent.

## Database location

| Item | Default location |
|---|---|
| Database | `%LOCALAPPDATA%\MoneyManager\money_manager.db` (plus `-wal` / `-shm` files while the app is open) |
| Logs | `%LOCALAPPDATA%\MoneyManager\logs\money_manager.log` (rotated) |
| Automatic safety copies | `%LOCALAPPDATA%\MoneyManager\money_manager.backup-*.db` |
| Saved API key | Windows Credential Manager → `MoneyManager/anthropic_api_key` |

Settings → *Local data storage* shows the paths in use and has an *Open data
folder* button. You can use a different folder with `data_dir` or
`MONEY_MANAGER_DATA_DIR` (see *Configuration*). The app writes nothing inside
its program folder unless you configure that.

The app writes safety copies automatically before a database upgrade
(`backup-<revision>-<time>`), before importing a backup (`backup-before-import`),
before a reset (`backup-before-reset`) and before restoring a copy
(`backup-before-restore`). **Settings → Safety copies** lists them, with what
each contains, and restores one. Your current data is saved as a new copy
first, so a restore can be undone too. For your own backups, use
**Settings → Export backup**. It writes one verified JSON file that *Import
backup* can restore.

## Troubleshooting

| Problem | What to do |
|---|---|
| *"Windows protected your PC"* | The executable is not code-signed. Choose **More info → Run anyway**. |
| The antivirus quarantines `MoneyManager.exe` | This is a false positive, which is common with PyInstaller programs. Restore the file and add an exception for the program folder, or run from source. |
| *"… is not a valid Win32 application"* / missing DLL | Extract the complete zip. `MoneyManager.exe` must stay next to its `_internal` folder, and copying the exe on its own does not work. Windows must be 64-bit. |
| The app shows an error at start-up and closes | Read the message, then look at the log (see *Database location*). Common causes: the data folder is not writable, or `MoneyManager.ini` has an invalid value. Start with `MONEY_MANAGER_LOG_LEVEL=DEBUG` for more detail. |
| *"The database was created by a newer version"* | You started an older version on newer data. Use the newer version; the older one refuses to change the data. |
| Something looks wrong with the program itself | Run `MoneyManager.exe --self-test C:\Temp\mm-check` and read `C:\Temp\mm-check\report.json`. The test uses its own temporary data. |
| Local AI: *"not running"* / no models found | Start Ollama, run `ollama list` to check that a model is installed, and check the address in Settings (default `http://localhost:11434`). |
| Online AI: key rejected / 401 | The key is wrong or was revoked. Save a new key in Settings, and check whether an old `ANTHROPIC_API_KEY` environment variable is being used instead. |
| Online AI: timeout or no connection | Check the internet connection and any proxy. Raise the timeout in Settings (5–600 s). The rest of the app keeps working. |
| An import is refused | The file was changed or damaged (checksum), or it comes from a different version's data schema. Your current data has not been touched. |

When reporting a problem, include the version (shown in the sidebar and in
Settings → *About Money Manager*) and the relevant part of the log. Logs contain no amounts, prompts,
answers or API keys.

# Technical reference

The sections below document the rules the application implements.

## Dashboard definitions

- **Period:** the current month to date.
- **Available balance** (first card): total balance − money set aside in
  goals and other allocations. The caption shows both parts. Manual goals
  track money outside the app, so nothing is subtracted for them. Account
  balances elsewhere (Transactions page) stay the real amounts.
- **Income / expenses:** income and expense transactions only; balance
  adjustments change the balance but are not counted as income or spending.
- **Saved this month:** income − spending (shown as *Overspent* when negative).
  Spending = expenses − investment contributions (see Statistics below).
- **Balance history:** total balance at the end of each day (last 180 days).
- **Savings rate:** (income − spending) ÷ income. Good ≥ 20 %, fair ≥ 0 %.
- **Spending vs last month:** this month to date vs the same days of last
  month. Good if lower, fair up to +10 %.
- **Emergency runway:** total balance ÷ average monthly spending over the last
  three complete tracked months. Good ≥ 6 months, fair ≥ 3.

All figures come from `DashboardService.overview()` (one database session);
charts convert amounts to floats only to draw them.

## Project structure

```
src/money_manager/
├── __main__.py          Entry point (python -m money_manager)
├── app.py               Bootstrap: config → logging → database → window
├── selftest.py          --self-test: end-to-end check of a (packaged) build
├── core/                Qt-free infrastructure
│   ├── config.py        AppConfig: environment, MoneyManager.ini, data folders
│   ├── resources.py     Locates bundled files (source tree or PyInstaller build)
│   ├── errors.py        MoneyManagerError hierarchy
│   ├── exception_hook.py  Global handler for uncaught exceptions
│   └── logging_setup.py Rotating file + console logging
├── domain/              Financial model and rules (from Sprint 2)
├── ai/                  Optional AI layer (Sprint 11): providers, context, privacy, keys
├── services/            Use cases between UI and persistence (from Sprint 2)
├── persistence/         SQLAlchemy + SQLite
│   ├── base.py          Declarative base with naming conventions
│   ├── database.py      Engine, SQLite pragmas, sessions, initialisation
│   └── models/          ORM models
└── ui/                  PySide6 widgets (presentation only)
    ├── theme.py         Colours, type, spacing, stylesheet, fonts
    ├── assets/          Icons and the bundled fonts (OFL)
    ├── navigation.py    Sidebar
    ├── main_window.py   Sidebar + page stack
    ├── dialogs.py       Error dialogs
    ├── components/      Card, EmptyState, PageHeader
    └── pages/           Page registry, base page, placeholder and settings pages
tests/                   pytest suite
packaging/               PyInstaller spec, build script, icon, example INI, release notes
```

Layering rule: `core`, `domain`, `ai`, `services` and `persistence` never import
PySide6 or the UI; `ai` never touches the database. `tests/test_architecture.py`
enforces this.

## Financial rules (Sprint 2 engine)

- **Money is exact.** Amounts are `Decimal` values with two decimal places,
  wrapped in the `Money` type and stored as integer minor units (centimes).
  Floats are rejected; more than two decimals is rejected, never rounded.
- **Transactions are real money movement.** Types: `income`, `expense`,
  `adjustment_in`, `adjustment_out`. The amount is always positive; the type
  decides the direction.
- **Balance is derived, never stored:**
  `opening balance + income − expenses + adjustments in − adjustments out`.
  Editing or deleting a transaction automatically changes the result.
- **Opening balance** lives on the account with an opening date. Transactions
  before that date are rejected (the opening balance already includes them).
- **Correcting the balance** (`BalanceService.reconcile`) records an adjustment
  for the difference instead of overwriting anything.
- **Categories are user-created** (income or expense). Income/expense
  transactions need a matching category; adjustments take none. Used
  categories can be archived but not deleted.
- The database repeats the critical rules as CHECK and foreign-key constraints.

## Allocations (Sprint 3)

Allocations organise money that already exists; they never add money.

- **Available is derived, never stored:**
  `Available = total real balance − Σ allocation balances`.
  So `Available + Σ allocations = total balance` always holds, and the same
  money cannot be counted twice.
- **Allocation balance** = transfers in − transfers out + tagged income −
  tagged expenses.
- **Transfers** move money between allocations and Available. They create no
  transaction, so the real balance cannot change. The source must hold the
  full amount. A transfer can be undone only while the destination still
  holds the money.
- **How real transactions interact with allocations:**

  | Transaction                       | Real balance | Allocation | Available |
  |-----------------------------------|--------------|------------|-----------|
  | Expense, not tagged               | −            | —          | −         |
  | Expense tagged to an allocation   | −            | −          | —         |
  | Income, not tagged                | +            | —          | +         |
  | Income tagged to an allocation    | +            | +          | —         |
  | Balance adjustment (never tagged) | ±            | —          | ±         |

- **Allocation balances can never be negative.** Transfers, tagged
  transactions, edits, deletes and undos that would overdraw one are rejected.
- **Available can go negative only through real transactions** (money set
  aside was actually spent). This is reported as *over-allocated* with a
  shortfall, and nothing new can be allocated until money is moved back to
  Available.
- Archiving an allocation returns its money to Available (recorded as a
  transfer). Allocations with history cannot be deleted, only archived.
- `AllocationService.check_consistency()` audits the state: negative or
  archived-but-funded allocations, over-allocation, and a cross-check of the
  total against the independently computed account balances.

## Statistics (Sprint 6)

Every figure is computed deterministically by `domain/analytics.py` (pure
functions, exact `Decimal`/integer arithmetic, ratios rounded half-up to four
places). AI features may later interpret these results but never compute them.

| Metric | Definition |
|---|---|
| Income / Expenses | Income / expense transactions in the range |
| Investment contributions | Expenses in categories marked *investment* (Statistics → Investment categories…) |
| Spending | Expenses − investment contributions |
| Savings | Income − spending (investing counts as saving) |
| Savings rate | Savings ÷ income (undefined without income) |
| Investment rate | Investments ÷ income |
| Net change | Balance change over the range: income − expenses ± adjustments |
| Change vs previous | Compared with the equally long range immediately before |
| Month-over-month | Each calendar month vs the previous one; the current month vs the same days of last month |
| Spending trend | Daily average spending, second half of the range vs first half (±5 % = stable) |
| Recurring spending | Same description + category, ≥ 3 times, weekly (6–8 days) or monthly (26–35 days) gaps within ±40 %, amounts within 2×, still active; detected over the last 12 months |

Ranges: 7 days, 30 days, 3 months, 6 months, 1 year (all ending today) or a
custom range of up to ten years. Balance adjustments are corrections: they
change the balance and net change but are never income, spending or savings.

## Goals (Sprint 7)

A goal has a name, a target, an optional deadline and description, and one of
two ways of tracking its money:

- **Allocation-backed (recommended).** The goal's current amount *is* the
  balance of its allocation — derived, never stored. *Add money* moves money
  from Available into the allocation and *Withdraw* moves it back; both are
  ordinary transfers, so the total balance never changes. An allocation can
  back only one goal (enforced by the database), and spending tagged to that
  allocation lowers the goal. Goal money is therefore never counted twice.
- **Manual.** For money kept outside the app; the user records the amount.
  It is not part of any balance, allocation or statistic.

| Rule | Definition |
|---|---|
| Progress | current ÷ target (exact, may exceed 100 %; only the bar is capped) |
| Complete | current ≥ target |
| On track / behind | current vs a steady-saving line from the start date to the deadline |
| Overdue | deadline passed without reaching the target |
| Needed per month | remaining ÷ months left (at least one month) |

Targets must be positive; new deadlines cannot be in the past (an edit may
keep a deadline that has passed). Deleting a backed goal never deletes money:
the user chooses to keep it in the allocation or move it back to Available.

## Subscriptions (Sprint 8)

A subscription is a **schedule**, not a money movement: name, amount,
frequency (weekly, monthly, every 3 months, yearly), next payment date,
expense category, optional default account, and active/paused.

- **Nothing is automatic.** Each due date is confirmed by the user:
  *Record* creates exactly one real expense (validated like any transaction)
  and moves the schedule on; *Skip* moves on without a transaction.
- **No duplicates.** Only the schedule's next unconfirmed date can be
  confirmed; each (subscription, due date) pair can be confirmed once — also
  enforced by a unique database constraint — and dates more than 7 days ahead
  cannot be confirmed early.
- **No date drift.** Monthly/quarterly/yearly schedules keep their billing
  day: 31 Jan → 28 Feb → 31 Mar; a 29 Feb yearly date returns on leap years.
- **Monthly equivalent** = amount × payments per year ÷ 12 (52 / 12 / 4 / 1),
  exact and rounded half-up per subscription; totals add the rounded values.
- Paused subscriptions are excluded from totals and upcoming payments.
  Deleting a subscription never deletes the expenses already recorded.

## Investments (Sprint 9)

Tracking only: **no market data, no live prices, no recommendations.** An
investment (stock, ETF, crypto, gold or other) has contributions,
withdrawals and user-entered values.

- **Contribution paid from an account:** creates one real expense in an
  *investment* category (so the Statistics investment rate counts it),
  optionally paid from an allocation. The contribution reads its amount and
  date from that transaction; deleting the transaction deletes it, and it
  cannot be changed into income.
- **External contribution / withdrawal:** money outside the app; the balance
  is not touched. (If a sale's money returns to an account, record that
  transaction too.)
- **Net invested** = contributions − withdrawals. **Current value** = latest
  valuation (one per day; a new one the same day replaces it).
- **Returns only with sufficient data:** a valuation must exist and be dated on
  or after the latest contribution/withdrawal. Then
  profit = current value − net invested and return = profit ÷ net invested
  (only when net invested > 0). Otherwise the value is shown as
  *out of date* and no return is given.
- **Net worth** = account balance + known investment values (money sent to an
  investment already left the balance, so nothing is counted twice).

## Financial health engine (Sprint 10)

`domain/financial_analysis.py` (pure functions) and
`services/analysis_service.py` (one database session, a constant number of
queries) produce a `FinancialAnalysis` for any period: **fixed rules, no AI,
no judgements.** Its facts are measurable statements such as *"Expenses
increased by 18.0% compared with 2026-05-01 to 2026-05-15"*; a later AI step
may interpret them. `analysis_to_dict()` gives a JSON-ready form (decimal
strings, transaction descriptions left out unless asked for).

| Metric | Definition |
|---|---|
| Comparison period | Month to date → same days of last month; a whole month → the whole previous month; otherwise the equally long period just before |
| Spending ratio | Spending ÷ income (Sprint 6 definitions of spending, savings and investments) |
| Income / expense / balance trends | Last ≤ 6 complete months since tracking began; average of the newer half vs the older half (±5 % = stable) |
| Category changes | Spending per category vs the comparison period |
| Category spike | ≥ 1.5 × the category's average over the previous 3 equal periods and the increase ≥ 5 % of this period's spending |
| New category | No spending in those periods and ≥ 10 % of this period's spending |
| Large expense | ≥ 3 × the median expense of its own category in those periods (≥ 3 earlier expenses) and ≥ 10 % of this period's spending |
| Recurring analysis | Recurring spending detected over 12 months (investment categories excluded), its monthly total, its share of the average monthly spending of the last 3 complete months, and which are not tracked as subscriptions |

**Only tracked history is compared.** Periods that start before the first
account's opening date are incomplete: they are never used as a baseline
for unusual spending, and a comparison with one is reported as *unavailable*
(the Statistics page shows "No comparison") instead of a misleading
percentage. Ratios are `None` when their base is zero or missing.

## AI providers (Sprint 11)

AI is **optional and off by default** (Settings → AI assistant). The layer in
`src/money_manager/ai/` follows the approved architecture:

```
AIProvider                      complete(request, consent) · check_availability(probe)
├── LocalAIProvider             data stays on this computer, no consent needed
│   └── OllamaProvider          Ollama HTTP API, standard library only
└── OnlineAIProvider            data leaves the computer: consent required per request
    └── AnthropicProvider       Claude API via the optional `anthropic` SDK
```

| Part | File | Role |
|---|---|---|
| Settings | `ai/settings.py` | Mode (off / local / online), Ollama address and model, Claude model (default `claude-opus-5`), timeout 5–600 s. Stored as JSON in the `settings` table (migration 0006). |
| Context | `ai/context.py` | Formats the Sprint 10 `FinancialAnalysis` as labelled text (income, expenses, savings rate, largest category, category changes, trends, unusual spending, recurring totals). |
| Prompt | `ai/prompts.py` | Fixed instructions + `<financial_analysis>` block + the question. Rules: use only the given figures, no investment recommendations, treat the data as data. |
| Privacy | `ai/privacy.py` | `DataDisclosure` (warning, destination, what is and is never sent, exact text) and `OnlineConsent`. |
| Keys | `ai/secrets.py` | `ApiKey` (hidden from `repr`/logs), Windows Credential Manager store, `ANTHROPIC_API_KEY` fallback. |
| Service | `services/ai_service.py` | `prepare(question)` → review → `send(prepared, consent)`. |

**Privacy rules, enforced in code and tested:**

- The AI receives the deterministic analysis, never the database. Transaction
  descriptions, individual transactions and their dates, account/goal/
  subscription/investment names and recurring-expense labels are never
  included. Category names can be replaced by neutral labels and the balance
  left out (`ContextOptions`).
- An online provider refuses to send without an `OnlineConsent` for exactly
  the reviewed payload (a SHA-256 fingerprint) and destination. Consent is only
  obtainable by accepting a `DataDisclosure`; the consent dialog keeps *Send*
  disabled until "I understand that this information will leave my computer"
  is ticked, and Cancel is the default. The provider is fixed when the request
  is prepared, so changing settings afterwards cannot redirect it.
- The local provider only accepts loopback addresses (`localhost`, `127.x`,
  `::1`), ignores system proxies and refuses Ollama *cloud* models (which run
  on Ollama's servers).
- API keys are never hard-coded, never in the database, settings or
  repository, and never logged: the log formatter redacts key-like strings
  (tracebacks included) and HTTP client libraries log at WARNING only. Logs
  record provider, model, duration and character counts, never prompts or
  answers.

**Setup.** Local: install [Ollama](https://ollama.com), `ollama pull <model>`,
then choose *Local model* and *Find installed models*. Online:
`pip install -e ".[ai-online]"`, choose *Online*, save an Anthropic API key
(kept in the Windows Credential Manager) or set `ANTHROPIC_API_KEY`.
*Test connection* checks the provider without sending financial data. For
`claude-opus-5` and `claude-fable-5-1`, requests enable Anthropic's
server-side fallback (`fallbacks: "default"`), which retries a request
declined by a safety classifier on another model.

## AI Advisor (Sprint 12)

The *AI Advisor* page combines two layers:

1. **Financial summary (no AI).** Income, expenses, savings rate, net change
   and the Sprint 10 facts for the chosen period (this month, last month, last
   3 or 12 months). It works the same with AI off, unavailable or failing.
2. **AI interpretation (optional).** *Insights*, *Suggestions*, *Spending
   analysis*, *Monthly summary*, or a free question. The AI receives the
   engine's figures (see *AI providers*) and is instructed to interpret them,
   never to calculate, estimate or invent numbers or transactions, and to say
   when data is unavailable.

| Behaviour | Rule |
|---|---|
| No arithmetic by the AI | Every total, difference and percentage is in the analysis. `ai/verification.py` checks each amount and percentage in an answer against it (rounding allowed, e.g. 23.5% → "about 24%") and the page flags any that are not found. |
| Provider selection | The page switches between off / local / online; details (model, key) are in Settings. |
| Online privacy | Every request shows the consent dialog (destination, what is and is never sent, exact text); nothing is sent until the user confirms. |
| Local privacy | The page states that the summary is processed on this computer; no confirmation is needed. |
| Failures | Errors appear on the page; the summary and the rest of the app keep working. Requests run on a worker thread, so the window stays responsive. |
| History | Each answer is stored locally (`ai_insights` table, migration 0007) with the exact analysis the AI received ("What the AI received"); newest 200 are kept; delete one or clear all. |
| Regenerate | Asks again with the same task/question and period, using the latest data and the currently selected provider; the old answer is kept. |

## Settings, backup and privacy (Sprint 13)

The Settings page has: local data storage, currency, AI assistant, export and
import, privacy, reset, and application information.

| Setting | Rule |
|---|---|
| Currency | Default **MAD**. One base currency for all amounts; no conversion and no exchange rates. It can be changed only while no account exists. Supported currencies are listed in `domain/currency.py` (two-decimal currencies; adding one is one entry). Stored in the `settings` table; the services and window are rebuilt after a change. |
| AI provider | Off (default), Local, Online, or **Automatic**: the local model when Ollama is running with it, otherwise online. Online requests always need confirmation, in every mode. |
| Data folder | Shown with an *Open data folder* button. To use another folder, set `data_dir` in `MoneyManager.ini` or `MONEY_MANAGER_DATA_DIR` (see *Configuration*); moving it from inside the app is not offered, so a move can never lose data halfway. |

**Export backup** writes every row of every table (as stored: integer minor
units, ISO dates, IDs) to a JSON file with the schema revision and a SHA-256
checksum. The file is written to a temporary name, renamed, then read back and
verified. API keys are never in the database, so never in a backup.

**Import backup** validates the whole file first (format, version, schema
revision, checksum, tables, columns and value types), writes a safety copy of
the current database (`money_manager.backup-before-import-<time>.db`), then
replaces all data in one transaction and checks foreign keys before
committing; any failure rolls back and leaves the current data untouched.
Backups from a different schema version are refused.

**Export transactions (CSV)** writes a spreadsheet-friendly file (UTF-8 with
BOM, signed decimal amounts); text that a spreadsheet would run as a formula
is prefixed with `'`.

**Reset** deletes all data only after typing `RESET` (checked by the service
as well as the dialog), writes a safety copy of the database first
(`…backup-before-reset-<time>.db`), and can also remove the saved API key.

## UI and performance (Sprint 14)

**Keyboard:** Ctrl+1…Ctrl+9 open the pages in sidebar order · Ctrl+N runs the
page's main action (add transaction, new goal, …) · Ctrl+F jumps to the search
field · F5 recalculates the page · Enter edits and Delete removes the selected
transaction. Every control shows a focus ring when reached with the keyboard.

**Design system** (`ui/theme.py`): colour tokens (`Colors`), a type scale
(`FontSize`, 11–36 px) and spacing (`Spacing`); the stylesheet uses nothing
else, which a test checks. The look follows the *Money Manager v3* design:
- **Colour:** a near-black ground and rounded tiles. One lime accent marks the
  main action. Each page also has its own pastel colour (`theme.PAGE_FILLS`),
  used for its navigation pill, header mark and headline figure tile.
- **Navigation:** an icon rail that slides open to show labels when the pointer
  is on it or it is reached with Tab. Clicking does not leave it open.
- **Page header:** a mono description line and a bold title. Every header also
  carries the window-wide controls:
  - *Search entries* opens Transactions with the search filled in.
  - *Ask AI* opens the AI Advisor with the cursor in the question box.
  - *New entry* opens the transaction dialog. It is lime only on pages without
    their own main action, and is hidden on Transactions, which has its own.

  On narrow windows the actions move under the title and wrap.
- **Type:** Space Grotesk for text, JetBrains Mono for figures (stat tiles and
  amounts). Both are bundled in `ui/assets/fonts` under the SIL Open Font
  License (licence files alongside).
- **Charts:** the categorical palette (a lime step of the accent, then violet,
  orange, blue and yellow) and the blue/orange income-vs-expenses pair are
  validated for colour-vision deficiency and contrast on the tile surface.
  The design's pastels are too light to use as chart marks.
- **Motion** (`ui/motion.py`):
  - a short launch screen;
  - tiles rise in one after another when a page opens;
  - figures count up;
  - bars and goal rings fill;
  - the rail's highlight glides to the current page;
  - a notice confirms each added, edited or deleted entry.

  Every animation ends in exactly the still state; while a figure counts, code
  and screen readers only ever see the exact value. Motion is off when it is
  switched off in Settings → Appearance, when Windows' "Show animations in
  Windows" is off, or with `MONEY_MANAGER_MOTION=off` (set for the tests).
- **Details:**
  - figures step down a size rather than being clipped;
  - goal cards show progress rings in each goal's colour;
  - transaction rows carry a badge in their category's colour (stable per id,
    `theme.identity_color`);
  - the dashboard has a "Renewing soon" tile with the next subscription
    payments.

Each page's main action sits in the page header;
empty pages show one centred call to action. Paired cards sit side by side on
wide windows and stack on narrow ones (`AdaptiveRow`), filter and button rows
wrap (`FlowRow`), and a test checks that no page is wider than the smallest
window (960 × 600).

**Performance**, measured with 200,000 transactions:

| | Before | After |
|---|---|---|
| Transactions page | 0.93 s | 0.08 s |
| Statistics page | 2.26 s (window frozen) | 0.19 s on screen, figures calculated in the background (0.6 s) |
| AI Advisor summary | 1.50 s | 0.23 s |
| Dashboard | 0.32 s | 0.18 s |
| Revisiting a page with unchanged data | full recalculation | no database queries |

How: covering indexes for the balance, ledger and expense queries
(migration 0008), a per-category median instead of one per expense in the
unusual-spending rule, a data revision counter so pages skip recalculating
when nothing changed (`Database.revision`, `AppServices.freshness()`), and
Statistics computed on a worker thread with an "Updating…" state (a newer
range supersedes an older request). `PRAGMA optimize` runs when the database
closes.

## Accounts, allocations, statement import, transfers, budgets and safety copies

**Money / Allocations page** (`ui/allocations`) shows Available, the total
balance and what is set aside, plus one card per allocation with its share and
the goal it backs. From each card you can add money, take money out, rename it,
or archive it (its money returns to Available; goal-backed allocations are
managed from their goal). The page also lists recent moves with *Undo*
(refused when the money has moved on) and archived allocations with *Restore*.
When more is set aside than you have, it explains by how much.

**Bank statement import** (Transactions → *Import…*):
- **Reading** (`domain/statement.py`) is pure. It detects the separator (`;`,
  `,` or tab) and the encoding (UTF-8 or Windows-1252, common for French bank
  exports), and guesses the columns from French and English headers (Date
  opération, Libellé, Montant, Débit/Crédit, Amount…). Columns named after a
  date are never taken as amounts.
- **Amounts** may use either decimal separator and thousands grouping, a minus
  sign, a trailing minus or parentheses; more than two decimals is refused,
  never rounded.
- **The date format** is the first one that reads every date in the file (day
  first before month first).
- **The dialog** previews every line as *New*, *Already recorded* or the reason
  it cannot be read. You choose the account and the categories for imported
  spending and income.
- **Importing** (`StatementImportService`) skips lines already in the account
  (same date, signed amount and description; matches are counted, so repeated
  identical lines are handled). Every other line is recorded like an entry typed
  by hand, in one unit of work, and lines that cannot be recorded are reported
  by line number.
- **Category rules** (`domain/categorize.py`, `CategoryRuleService`): a rule is
  a keyword and a category. A line whose description contains the keyword as
  whole words (case and accents ignored) goes to that category; the longest
  matching keyword wins, and income and spending rules are kept apart. Changing
  an entry's category on the Transactions page learns a rule from the first
  meaningful word of its description (card and transfer words, city names and
  numbers are skipped). The preview shows each line's category; rules are listed,
  added and removed in Settings → Category rules, and deleted with their category.

**Cash-flow forecast** (dashboard, `domain.forecast`, `ForecastService`): the
projected balance for the next 6 months, day by day. It starts from today's
total balance and adds every date of the active recurring entries and
subscriptions (dates due but not yet recorded count today), the loans due in
the period (what is left), and your usual income and spending: the average of
the last complete months (up to three) minus the monthly cost of what is
already scheduled, spread evenly over the days. The card names the lowest point,
or warns when the balance goes below zero; the table lists every scheduled item
with the balance after it.

**Reminders** (Settings → Notifications, `domain.reminders`): Windows
notifications from the notification-area icon for payments due today or
tomorrow (or overdue), budgets near or over their limit, loans due within three
days, and a forecast below zero within 30 days. Each reminder has a key and is
shown once (keys are kept 60 days). Optionally Money Manager keeps running in
the notification area when its window is closed — locked, when the app lock is
on. Clicking a notification opens the page it is about.

**Arabic** is the third interface language (`core/locales/ar.py`): the whole
window is mirrored right to left (the navigation rail moves to the right),
months use the Moroccan names (يناير … دجنبر), amounts keep Western digits and
are written like in French (12 000,50 MAD), held left to right inside Arabic
text. Charts and PDF reports follow; online AI answers in Arabic. A context
mechanism (`trc`) lets one English word take different translations (the
transaction type *Income* is "Revenu" / "دخل", the heading "Revenus" /
"المداخيل").

**Code signing** (`packaging/build.py`): when a code-signing certificate is
configured, the build signs `MoneyManager.exe` and the Setup with signtool
(SHA-256, RFC 3161 timestamp), which removes Windows' unknown-publisher
warning. Configure it with environment variables only: `MM_SIGN_CERT` (a .pfx)
and `MM_SIGN_PASSWORD`, or `MM_SIGN_THUMBPRINT` (a certificate installed in
Windows); optionally `MM_SIGNTOOL` and `MM_SIGN_TIMESTAMP`. Without them the
build is unsigned, as before. Certificates come from a certificate authority
(OV or EV code-signing) or from Microsoft's Trusted Signing service.

**Accessibility**: every button, field and list on every page has a name for
screen readers (`tests/ui/test_accessibility.py` checks it).

**Languages** (Settings → Appearance → Language): English, French, or the same
as Windows. Every text goes through `core.i18n.tr`; translations live in
`core/locales/fr.py` (English text → French, `str.format` placeholders kept).
`tests/test_i18n.py` fails when a text has no translation or a translation's
placeholders differ, and the whole app is clicked through in French. Numbers
and dates follow the language (`12 000,50 MAD`, `38,2 %`, `05 mars 2026`).
Online AI answers in the interface language.

**Loans and debts** (Accounts page, `DebtService`): money you lent (owed to
you) or borrowed (you owe). When the money moves through an account it is a
balance adjustment — never income or spending — recorded together with the
loan or repayment; undoing a repayment removes its adjustment. What is still
owed counts in net worth (dashboard chart, Investments page, reports).

**Receipts** (Transactions → *Receipts…*, `ReceiptService`): photos or PDFs up
to 10 MB attached to an entry; type, size and file signature are checked. They
are stored in the database, so backups (base64 in the JSON), safety copies,
restores and resets include them; deleting the entry deletes them.

**Password-protected backups** (Settings → Export and import): the backup JSON
encrypted with AES-256-GCM, key from scrypt (random salt and nonce per file).
Import asks for the password; a wrong password or a changed byte is detected.
A forgotten password cannot be recovered.

**Yearly report** (Statistics → *Yearly report…*): totals vs the same days of
the previous year, month by month with a chart, best and hardest month, net
worth over the year, spending by category and the largest expenses.

**Update check** (Settings → Updates, off by default): once a day at most, an
HTTPS request to GitHub for the latest release number — nothing about you or
your data is sent. A newer version is announced with a link; nothing is
downloaded or installed by itself.

**Monthly report** (Statistics → *Monthly report…*, `ReportService`,
`ui/reports/monthly_pdf.py`): a two-page A4 PDF of one month — income,
spending, invested and saved compared with the month before (the current month
with the same days of last month), balance and net worth with a chart, budgets,
goals, spending by category with a chart, and the largest expenses. It is laid
out by Qt (`QTextDocument` → `QPdfWriter`), entirely on your computer; names and
descriptions are escaped.

**Recurring entries** (Transactions → *Recurring…*, `RecurringService`): income
or expenses recorded automatically on a schedule (weekly, monthly, every 3
months, yearly; the day of the month is kept and clamped to short months). Due
dates are recorded at start-up and hourly while the app is open; each
transaction and the schedule's move to its next date are one unit of work, so a
date is never recorded twice. A first date in the past records the dates since
then (at most a year back). Paused entries skip the dates missed while paused; a
date that cannot be recorded (e.g. an archived category) is reported and tried
again later. Subscriptions remain confirmed one payment at a time.

**App lock** (Settings → App lock, `ui/lock`): Windows Hello (PIN, fingerprint
or face, through the Windows Runtime `UserConsentVerifier`; the app only learns
"verified" or not). When on, the app starts locked and locks after 1/5/15/30
minutes without use or on Ctrl+L; the lock screen covers every page, open
dialogs are closed and shortcuts are paused. Turning the lock on or off asks
Windows Hello first. It keeps people who use your computer out of the app; it
does not encrypt the data file. If Windows Hello stops being available, the
screen explains it and lets you in rather than locking you out.

**Themes** (Settings → Appearance): dark (default), light, or the same as
Windows' app mode. Colour tokens switch before the windows are built, so a new
theme applies after a restart (*Restart now*).

**Installer** (`packaging/installer`): `install_core.py` (tested) extracts the
release next to the previous version and swaps the folders, carries over files
you added to the program folder (e.g. `MoneyManager.ini`), writes
`install-manifest.json` and `uninstall.ps1`, creates shortcuts and the Apps &
features entry under HKCU. The uninstaller removes only the listed items, the
shortcuts and that entry. `build.py` builds the Setup and checks it with a quiet
install into a temporary folder.

**Net worth over time** (dashboard, `NetWorthService`): one point per month for
the last 12 months, from the month the first account was opened. Each point is
the total balance at the month's last day (today for the current month) plus,
for each active investment, the latest value entered on or before that day
(investments not valued yet count as nothing, as on the Investments page). The
hover and the table show balance, investments and net worth separately.


**Accounts page** (`ui/accounts`) lists every account with its balance from
`BalanceService`, largest first. It also shows each account's share of what you
have, what you owe (accounts below zero, e.g. cards), and its activity since
tracking began. From there you can create, rename or delete an account (only
one without transactions) and transfer money. *Correct balance* records the
difference from the balance your bank shows as an adjustment, via
`BalanceService.reconcile`; it never overwrites the balance.

**Daily copies:** once a day, at start-up and only when there is data, the app
writes `money_manager.backup-daily-<time>.db` next to the database and keeps
the newest 30. Other safety copies are never pruned. Switch it off in
Settings → Safety copies.

**Transfers between accounts** (Transactions → *Transfer*, `AccountTransferService`)
move money between two of your accounts, e.g. from the bank to the cash wallet.
- A transfer is stored as two balance adjustments, out of one account and into
  the other, tied together by an `account_transfers` row (migration 0009).
  Totals therefore never change, and a transfer is never income, spending or
  savings.
- Both sides are created in one unit of work and deleted together. Neither side
  can be edited or deleted alone; the database refuses that as well (RESTRICT).
- The list shows them as *Transfer* with "To …" / "From …", and CSV exports
  label them *Transfer out* / *Transfer in*.
- *New account* on the same page adds the second account.

**Budgets** (`domain/budgets.py`, `BudgetService`, migration 0010) are monthly
limits per expense category. Each one compares the category's expenses in the
current calendar month with the limit:

| Status | Rule |
|---|---|
| Over | spent > limit |
| Near limit | spent ≥ 85 % of the limit (exact comparison) |
| On track | otherwise |

From the 3rd day of the month, a projection shows the month-end spending at
the pace so far. One budget per category; deleting an unused category deletes
its budget.

**Safety copies** (`DataService.safety_copies` / `restore_safety_copy`): only
copies listed next to the database can be restored.
- The copy is checked (`PRAGMA integrity_check`) and duplicated into a temporary
  folder. Older copies are upgraded there first, so the copy itself is never
  changed.
- Its rows then replace all data exactly like an import: after a safety copy of
  the current data, in one transaction, with references checked before
  committing.

## Database migrations

The schema is versioned with Alembic (`persistence/migrations`). On start-up
the app creates a new database, adopts one created before migrations existed,
or upgrades an older one. **Before any schema change the database is backed
up** next to the original as `money_manager.backup-<revision>-<timestamp>.db`.
A database from a newer app version is refused rather than modified.

## Error handling

- Expected failures raise a `MoneyManagerError` subclass (`ConfigurationError`,
  `DatabaseError`) with a message that is safe to show to the user.
- Startup failures show a dialog and exit with code 1.
- Any other uncaught exception — including ones raised in Qt slots — is logged
  with a full traceback and the user sees a generic error dialog.
- Logs never contain financial amounts; SQLAlchemy's SQL logging is silenced
  for that reason.
