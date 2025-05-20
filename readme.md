# Shared Expenses with Roles API

**A Django REST Framework solution for tracking group expenses, managing balances, and simplifying repayments**  

---

## 📖 Overview  
A backend API designed to help friends, roommates, or travel groups track shared expenses, split costs (equally or by percentage), and maintain transparent financial records. Features secure group management, detailed expense tracking, and automated balance calculations.

**Key Features**:
- Token-based authentication
- Group creation & member invitations
- Expense tracking with custom splits
- ↔Debt repayment recording
- Real-time balance summaries


## Installation

Clone the repository:

```bash
git https://github.com/Just-Mike4/sharedgoals.git
cd sharedgoals
```

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply the database migrations:

```bash
python manage.py migrate
```

Run the development server:

```bash
python manage.py runserver
```

## API Endpoints Documentation

## POST `/api/register/`
Create a new user account.  
**Request Body:**
```json
{
    "username": "tina",
    "email": "tina@example.com",
    "password": "strongpassword"
}
```
**Response:**
```json
{
  "username": "john",
  "email": "john@example.com",
  "token": "d65b24fe38a0456a8c..."
}
```


## POST `/api/login/`
Get authentication token.  
**Request Body:**
```json
{
    "username": "tina",
    "password": "strongpassword"
}
```
**Response:**
```json
{
  "token": "d65b24fe38a0456a8c..."
}
```

## POST `/api/password-reset/`

Request a password reset link to be sent to the user's email.
**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response:**

```json
{
  "message": "Password reset link sent"
}
```


## POST `/api/password-reset-confirm/<uid>/<token>/`

Confirm the password reset using the unique link and set a new password.
**Request Body:**

```json
{
  "new_password": "NewSecurePassword123"
}
```

**Response:**

```json
{
  "message": "Password has been reset"
}
```


### 🔹 POST `api/groups/`
Create a new group.

**Request Body:**
```json
{
    "name": "Roommates Budget"
}
```
**Response:**
```json
{
    "id": 1,
    "name": "Roommates Budget",
    "created_by": "tina",
    "members": [
        {
        "username": "tina",
        "role": "admin"
        }
    ]
}
```


### 🔹 POST `api/groups/{group_id}/invite/`
Invite users to the group.

**Request Body:**
```json
{
    "username": "kelvin"
}
```
**Response:**
```json
{
    "detail": "User kelvin added to the group"
}
```


### 🔹 GET `api/groups/`
List groups current user belongs to.

**Response:**
```json
[
{
    "id": 1,
    "name": "Roommates Budget",
    "created_by": "tina",
    "members": [
        {
        "username": "tina",
        "role": "admin"
        }
    ]
},
{
    "id": 1,
    "name": "Savingbuddies",
    "created_by": "tina",
    "members": [
        {
        "username": "tina",
        "role": "member"
        }
    ]
}
]
```

### 🔹 GET `api/groups/{group_id}/`
View group details with members and recent expenses.
**Response:**
```json
{
    "id": 1,
    "name": "savingbuddies",
    "created_by": "Mastermike",
    "members": [
        {
            "username": "Mastermike",
            "role": "admin"
        },
        {
            "username": "bossmmike",
            "role": "member"
        }
    ],
    "recent_expenses": []
}
```


### 🔹 POST `/groups/{group_id}/expenses/`
Add an expense.

**Request Body:**
```json
{
    "title": "Groceries",
    "amount": 6000,
    "paid_by": "tina",
    "shared_between": [
        {"username": "tina", "share": 50},
        {"username": "kelvin", "share": 50}
    ],
    "description": "Monthly grocery run",
    "date": "2025-04-21"
}
```
**Response:**
```json
{
    "id": 3,
    "title": "Groceries",
    "amount": 6000,
    "paid_by": "tina",
    "shares": [
        {"username": "tina", "owes": 3000},
        {"username": "kelvin", "owes": 3000}
    ]
}
```


### 🔹 GET `/groups/{group_id}/expenses/`
List all expenses in a group (optional filter by member/date).
**Response:**
```json
[
    {
        "id": 1,
        "title": "Groceries",
        "amount": "6000.00",
        "date": "2025-04-21",
        "description": "Monthly grocery run",
        "paid_by": "Mastermike",
        "shares": [
            {
                "username": "Mastermike",
                "share": "50.00"
            },
            {
                "username": "bossmmike",
                "share": "50.00"
            }
        ]
    }
]
```

### 🔹 GET `/groups/{group_id}/summary/`
Show "who owes whom" based on all expenses.

**Response:**
```json
{
    "summary": [
        {
            "from": "kelvin",
            "to": "tina",
            "amount": 3500
        }
    ]
}
```


### 🔹 POST `/groups/{group_id}/repayments/`
Log a repayment between members.

**Request Body:**
```json
{
    "from_user": "kelvin",
    "to_user": "tina",
    "amount": 1000,
    "date": "2025-04-22"
}
```

**Response:**
```json
{
    "id": 1,
    "from_user": "kelvin",
    "to_user": "tina",
    "amount": "3000.00",
    "date": "2025-06-22"
}
```

### 🔹 GET `/groups/{group_id}/repayments/`
List all repayments.

**Response:**
```json
[
    {
    "id": 1,
    "from_user": "kelvin",
    "to_user": "tina",
    "amount": "3000.00",
    "date": "2025-06-22"
    }
]
```


### 🔹 GET `/groups/{group_id}/balances/`
Shows net balance for each group member (including repayments).

**Response:**
```json
[
    {"username": "tina", "balance": +2000},
    {"username": "kelvin", "balance": -2000}
]
```