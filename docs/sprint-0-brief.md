# Money Manager — Sprint 0 Brief

You are building a production-quality Windows desktop personal money-management application called "Money Manager".

## Tech Stack

- Python 3.12+
- PySide6
- SQLite
- SQLAlchemy
- Pydantic where useful
- Matplotlib and/or PyQtGraph
- pytest
- Alembic if migrations are necessary
- PyInstaller for Windows packaging

IMPORTANT: Do NOT implement the application yet. This sprint is ONLY architecture and planning.

## Product Requirements

The application will allow the user to:

- Modify their balance when appropriate.
- Add income and expenses.
- Create unlimited custom categories.
- Manage investments.
- Manage subscriptions.
- Manage bills.
- Manage savings.
- Create financial goals.
- Organize existing money into allocations.
- View a financial dashboard.
- View financial statistics and graphs.
- Analyze whether spending/saving behavior is improving or worsening.
- Receive personalized AI financial insights.
- Support both local AI and online AI.
- Keep the financial database locally on the user's Windows computer.
- Use MAD as the initial currency.

## Very Important Financial Architecture

There must be a distinction between:

### 1. Real Financial Transactions

Transactions represent actual money entering or leaving the user's money.

Example:

```
Salary          +12,000 MAD
Restaurant        -300 MAD
Investment       -2,000 MAD
Subscription      -200 MAD
```

The balance is derived from actual financial activity.

### 2. Allocations

Allocations represent how existing money is organized/reserved.

Example:

```
Total balance:        30,000 MAD

Savings:               8,000 MAD
Investments:           5,000 MAD
Bills:                 3,000 MAD
Subscriptions:         1,000 MAD
Available:             13,000 MAD
```

Moving 500 MAD from Available to Investments must NOT change total balance.

```
Available:    13,000 -> 12,500
Investments:   5,000 ->  5,500
Total remains: 30,000 MAD
```

Actual transactions DO change the real balance.

The architecture must prevent double-counting.

## AI

The application must support:

- Local AI provider
- Online AI provider

Use an abstraction such as:

```
AIProvider
├── LocalAIProvider
└── OnlineAIProvider
```

The financial database remains local.

Never silently send financial data to an online provider.

The application should calculate financial metrics deterministically before sending structured information to AI.

Possible financial metrics:

- Current balance
- Monthly income
- Monthly expenses
- Savings
- Savings rate
- Investment contributions
- Investment rate
- Category spending
- Month-over-month changes
- Recurring expenses
- Balance trends

## Potential Entities

- Account
- Category
- Transaction
- Allocation
- AllocationTransfer
- Goal
- Subscription
- Investment
- FinancialSnapshot
- AIInsight
- UserSettings

The model may be modified if there is a better architecture.

## Sprint 0 Tasks

1. Analyze the requirements.
2. Identify ambiguities.
3. Design the complete application architecture.
4. Design the database schema.
5. Define relationships.
6. Define financial calculation rules.
7. Define allocation rules.
8. Define transaction rules.
9. Define AI provider architecture.
10. Define financial-health engine architecture.
11. Define project directory structure.
12. Define testing strategy.
13. Define error-handling strategy.
14. Define data/privacy strategy.
15. Define the complete sprint roadmap.

## Pay Special Attention To

- Monetary precision.
- Avoiding floating-point errors.
- Preventing double-counting.
- Database consistency.
- Separation between UI, business logic, and database.
- Keeping AI optional.
- Keeping financial data local.

## Expected Sprint 0 Deliverable

1. Architecture
2. Database schema
3. Entity relationships
4. Financial rules
5. Allocation rules
6. AI architecture
7. Project structure
8. Testing strategy
9. Sprint roadmap
10. Important assumptions/questions

At the end, STOP and wait for approval.
