
from flask import Flask, render_template, request, redirect, jsonify, send_file, session, url_for, flash
import sqlite3, os, csv, json
from datetime import datetime, date
from collections import defaultdict
from werkzeug.security import generate_password_hash, check_password_hash

DB = "expenses_v2.db"

def init_db():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        income REAL DEFAULT 0,
        limits TEXT DEFAULT '{}'
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        amount REAL,
        category TEXT,
        note TEXT,
        created_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.commit()
    conn.close()

def query(sql, params=(), fetch=False):
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute(sql, params)
    if fetch:
        rows = cur.fetchall()
        conn.close()
        return rows
    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = os.environ.get('EXPENSE_SECRET') or 'dev-secret-please-change'
init_db()

CATEGORIES = ['Food', 'Travel', 'Bills', 'Shopping', 'Health', 'Other']

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    rows = query('SELECT id, username, income, limits FROM users WHERE id=?', (uid,), fetch=True)
    if not rows:
        return None
    r = rows[0]
    return {'id': r[0], 'username': r[1], 'income': r[2] or 0, 'limits': json.loads(r[3] or '{}')}

@app.route('/')
def index():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    rows = query("SELECT id, title, amount, category, note, created_at FROM expenses WHERE user_id=? ORDER BY created_at DESC LIMIT 100", (user['id'],), fetch=True)
    expenses = [dict(id=r[0], title=r[1], amount=r[2], category=r[3], note=r[4], created_at=r[5]) for r in rows]
    return render_template('index.html', expenses=expenses, categories=CATEGORIES, user=user)

@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        if not username or not password:
            flash('Enter username and password', 'error')
            return redirect(url_for('signup'))
        ph = generate_password_hash(password)
        try:
            query('INSERT INTO users (username, password_hash) VALUES (?,?)', (username, ph))
            flash('Account created — please log in', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Username already exists or error: ' + str(e), 'error')
            return redirect(url_for('signup'))
    return render_template('auth.html', action='signup')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','').strip()
        rows = query('SELECT id, password_hash FROM users WHERE username=?', (username,), fetch=True)
        if not rows:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))
        uid, ph = rows[0]
        if check_password_hash(ph, password):
            session['user_id'] = uid
            flash('Logged in successfully', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))
    return render_template('auth.html', action='login')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
def add():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    title = request.form.get('title','').strip()
    amount = float(request.form.get('amount',0) or 0)
    category = request.form.get('category','Other')
    note = request.form.get('note','').strip()
    created_at = request.form.get('date') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    query("INSERT INTO expenses (user_id, title, amount, category, note, created_at) VALUES (?, ?, ?, ?, ?, ?)", (user['id'], title, amount, category, note, created_at))
    return redirect(url_for('index'))

@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    query("DELETE FROM expenses WHERE id=? AND user_id=?", (id, user['id']))
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET','POST'])
def settings():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        income = float(request.form.get('income',0) or 0)
        # collect limits for categories
        limits = {}
        for c in CATEGORIES:
            val = request.form.get('limit_' + c, '') or '0'
            try:
                limits[c] = float(val)
            except:
                limits[c] = 0.0
        query('UPDATE users SET income=?, limits=? WHERE id=?', (income, json.dumps(limits), user['id']))
        flash('Settings updated', 'success')
        return redirect(url_for('settings'))
    # reload user after potential update
    user = current_user()
    return render_template('settings.html', categories=CATEGORIES, user=user)

@app.route('/report')
def report():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    return render_template('report.html', categories=CATEGORIES, user=user)

@app.route('/api/data')
def api_data():
    user = current_user()
    if not user:
        return jsonify({'error':'unauthorized'}), 401
    rows = query("SELECT id, title, amount, category, note, created_at FROM expenses WHERE user_id=?", (user['id'],), fetch=True)
    expenses = [dict(id=r[0], title=r[1], amount=r[2], category=r[3], note=r[4], created_at=r[5]) for r in rows]
    total = 0.0
    by_cat = defaultdict(float)
    by_month = defaultdict(float)
    highest = None
    for e in expenses:
        amt = float(e['amount'] or 0)
        total += amt
        by_cat[e['category']] += amt
        # parse date
        try:
            dt = datetime.fromisoformat(e['created_at']) if 'T' in e['created_at'] else datetime.strptime(e['created_at'], '%Y-%m-%d %H:%M:%S')
        except:
            dt = datetime.now()
        mon = dt.strftime('%Y-%m')
        by_month[mon] += amt
        if highest is None or amt > highest['amount']:
            highest = e
    # compute this month's spending
    this_month = date.today().strftime('%Y-%m')
    spent_this_month = sum(v for k,v in by_month.items() if k==this_month)
    income = user.get('income',0) or 0
    savings = income - spent_this_month
    limits = user.get('limits', {}) or {}
    return jsonify({
        'total': total,
        'by_category': by_cat,
        'by_month': by_month,
        'highest': highest,
        'expenses': expenses,
        'income': income,
        'savings': savings,
        'limits': limits,
        'spent_this_month': spent_this_month
    })

@app.route('/export')
def export_csv():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    rows = query("SELECT id, title, amount, category, note, created_at FROM expenses WHERE user_id=? ORDER BY created_at DESC", (user['id'],), fetch=True)
    csv_path = f'expenses_user_{user["id"]}_export.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id','title','amount','category','note','created_at'])
        writer.writerows(rows)
    return send_file(csv_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
