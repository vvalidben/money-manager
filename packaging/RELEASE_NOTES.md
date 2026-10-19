# Money Manager 1.2.0

A local-first personal finance application for Windows. Your data stays in a
database on your computer; nothing is sent anywhere unless you use online AI
and confirm each request.

## What's new in 1.2.0

- **Import your bank statement.** Transactions → *Import…* reads the CSV file
  your bank exports, including French statements with *Débit* / *Crédit*
  columns. You see every line before importing; lines already recorded are
  skipped, so importing the same statement twice adds nothing.
- **Money / Allocations page.** See what is set aside and what is Available;
  add or take out money; rename, archive or restore allocations; and undo a
  recent move.

## New in 1.1.0

- **New look.** Rounded tiles on a dark background, a colour for each page, an
  icon rail that opens when you point at it, and search, *Ask AI* and
  *New entry* on every page.
- **Animations.** A short launch screen; pages that rise into place; figures
  that count up; bars and goal rings that fill; and a notice confirming each
  change. Switch them off in Settings → Appearance. They also stay off when
  Windows' "Show animations" setting is off.
- **Accounts page.** All your accounts with their balances. Add, rename or
  delete accounts, and *Correct balance* to match what your bank shows.
- **Transfers between accounts**, e.g. bank → cash wallet. Your total stays the
  same, and a transfer never counts as income or spending.
- **Budgets.** A monthly limit per spending category, with what is left, a
  status (on track, near limit, over) and where you will end the month at your
  current pace.
- **Safety copies you can restore** from Settings → Safety copies. Money
  Manager now also saves a copy automatically once a day and keeps the last 30.
- **Details.** Goal progress rings, a colour badge for each category, and a
  "Renewing soon" tile on the dashboard. Large figures now shrink to fit
  instead of being cut off.

Your data is upgraded automatically the first time you start a new version (a safety
copy is saved first).

## What's included

- **Accounts and transactions:** income, expenses, balance corrections and
  transfers, with search, filters, CSV export and bank statement import. Amounts are exact to the
  centime.
- **Budgets:** monthly limits per spending category.
- **Allocations:** set money aside (e.g. Holiday, Emergency fund) without
  counting it twice; spending tagged to an allocation comes out of it.
- **Dashboard and statistics:** balance, income vs expenses, spending by
  category, trends, monthly comparisons and key facts for any date range.
- **Goals:** savings targets with deadlines, kept in allocations or tracked
  manually.
- **Subscriptions & bills:** recurring payments you confirm when they happen.
- **Investments:** contributions, withdrawals and the values you enter. There
  is no market data and no advice.
- **AI Advisor (optional):** explanations of your own figures by a local model
  (Ollama) or Anthropic's Claude. The exact text is shown before anything is
  sent online. AI is off unless you turn it on.
- **Backups:**
  - export and import of everything as one verified file;
  - safety copies before risky changes and once a day;
  - a reset protected by a typed confirmation.

## System requirements

- Windows 10 or 11, 64-bit
- About 400 MB of disk space
- Optional: [Ollama](https://ollama.com) for local AI, or an Anthropic API key
  and an internet connection for online AI

## Installing

1. Extract `MoneyManager-1.2.0-windows-x64.zip` to a folder of your choice,
   e.g. `%LOCALAPPDATA%\Programs\MoneyManager`.
2. Start `MoneyManager.exe`. You can pin it to Start or the taskbar.
3. Windows SmartScreen may warn about an unrecognised app because the
   executable is not code-signed. If so, choose **More info → Run anyway**.

**Updating:** replace the program folder with the new version. Your data is kept
separately and is upgraded automatically (a copy is saved first).

**Uninstalling:** delete the program folder. Also delete
`%LOCALAPPDATA%\MoneyManager` if you want to remove your data.

## First start

Money Manager creates `%LOCALAPPDATA%\MoneyManager` with the database and logs,
then shows the dashboard. Create your first account to begin. To keep data
elsewhere (e.g. portable use), see `MoneyManager.example.ini`.

## Privacy

- Data is stored only on this computer. There is no account, cloud sync or
  telemetry.
- Local AI processes data on this computer. Online AI sends a summary of your
  figures (never transaction descriptions or account names), and only after you
  review and confirm it.
- API keys are kept in the Windows Credential Manager, never in the database,
  backups or logs.

## Known limitations

- The executable is not code-signed, so SmartScreen may warn the first time.
- One currency for all amounts (MAD by default); there is no currency
  conversion.
- The first nine pages have Ctrl+1…Ctrl+9 shortcuts; AI Advisor and Settings
  have none.
