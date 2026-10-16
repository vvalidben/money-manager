# Money Manager 1.0.0

A local-first personal finance application for Windows. Your data stays in a
database on your computer; nothing is sent anywhere unless you use online AI
and confirm each request.

## What's included

- **Accounts and transactions** — income, expenses and balance corrections,
  with search, filters and CSV export. Amounts are exact to the centime.
- **Allocations** — set money aside (e.g. Holiday, Emergency fund) without
  counting it twice; spending tagged to an allocation comes out of it.
- **Dashboard and statistics** — balance, income vs expenses, spending by
  category, trends, monthly comparisons and key facts for any date range.
- **Goals** — savings targets with deadlines, kept in allocations or tracked
  manually.
- **Subscriptions & bills** — recurring payments you confirm when they happen.
- **Investments** — contributions, withdrawals and the values you enter
  (no market data, no advice).
- **AI Advisor (optional)** — explanations of your own figures by a local model
  (Ollama) or Anthropic's Claude, with the exact text shown before anything is
  sent online. AI is off unless you turn it on.
- **Backups** — export/import of everything as one verified file; reset with a
  safety copy.

## System requirements

- Windows 10 or 11, 64-bit
- About 400 MB of disk space
- Optional: [Ollama](https://ollama.com) for local AI, or an Anthropic API key
  and an internet connection for online AI

## Installing

1. Extract `MoneyManager-1.0.0-windows-x64.zip` to a folder of your choice,
   e.g. `C:\Program Files\MoneyManager` or `%LOCALAPPDATA%\Programs\MoneyManager`.
2. Start `MoneyManager.exe`. Pin it to Start or the taskbar if you like.
3. Windows SmartScreen may warn about an unrecognised app because the
   executable is not code-signed: choose **More info → Run anyway**.

To update, replace the program folder with the new version; your data is kept
separately and is upgraded automatically (a backup of the database is made
first). To uninstall, delete the program folder, and delete
`%LOCALAPPDATA%\MoneyManager` if you also want to remove your data.

## First start

Money Manager creates `%LOCALAPPDATA%\MoneyManager` with the database and logs,
then shows the dashboard. Create your first account to begin. To keep data
elsewhere (e.g. portable use), see `MoneyManager.example.ini`.

## Privacy

- Data is stored only on this computer. No account, cloud sync or telemetry.
- Local AI processes data on this computer. Online AI sends a summary of your
  figures (never transaction descriptions or account names) only after you
  review and confirm it.
- API keys are kept in the Windows Credential Manager, never in the database,
  backups or logs.

## Known limitations

- The **Money / Allocations** page is a placeholder in this version:
  allocations are created and funded through goals, and transactions can be
  tagged to them.
- The executable is not code-signed (SmartScreen warning on first start).
- One currency for all amounts (MAD by default); no currency conversion.
