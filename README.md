
Expense Tracker v2 (Flask) — Login, Multi-user, Category limits, Savings
---------------------------------------------------------------------
What's new:
- User signup/login with username + password (hashed)
- Multiple users: each user has separate expenses and settings
- Settings page: set monthly income and per-category limits
- Savings calculation (income - this month's spending)
- Limits shown in reports and warnings when exceeded

How to run:
1. Create a virtualenv and activate it.
   python -m venv venv
   source venv/bin/activate   # mac/linux
   venv\Scripts\activate    # windows
2. Install requirements:
   pip install -r requirements.txt
3. Run the app:
   python app.py
4. Open http://127.0.0.1:5000 in your browser.

Notes:
- The app creates 'expenses_v2.db' SQLite file in the project folder.
- Default categories: Food, Travel, Bills, Shopping, Health, Other
- For demo: sign up as a new user then add expenses & set limits.
