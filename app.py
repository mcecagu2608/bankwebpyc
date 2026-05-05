from flask import Flask, render_template, request, redirect
import sqlite3
import os

app = Flask(__name__)

# Base de datos local
dir_db = "data.db"

# -----------------------
# INIT DB
# -----------------------
def init_db():
    conn = sqlite3.connect(dir_db)
    c = conn.cursor()

    c.execute("PRAGMA foreign_keys = ON")

    # ACCOUNTS
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            currency TEXT DEFAULT 'EUR',
            initial_balance INTEGER DEFAULT 0
        )
    ''')

    # CATEGORIES
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL
        )
    ''')

    # Category defaults
    c.execute("SELECT id FROM categories WHERE name = ? AND type = ?", ("Ingreso", "income"))
    if not c.fetchone():
        c.execute("INSERT INTO categories (name, type) VALUES (?, ?)", ("Ingreso", "income"))
    c.execute("SELECT id FROM categories WHERE name = ? AND type = ?", ("Gasto", "expense"))
    if not c.fetchone():
        c.execute("INSERT INTO categories (name, type) VALUES (?, ?)", ("Gasto", "expense"))

    # TRANSACTIONS
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            category_id INTEGER,
            amount INTEGER NOT NULL,
            type TEXT NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES accounts(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# -----------------------
# HOME (LISTA TRANSACCIONES)
# -----------------------
@app.route('/')
def index():
    conn = sqlite3.connect(dir_db)
    c = conn.cursor()

    c.execute("SELECT id, name, type FROM categories ORDER BY type, name")
    categories = c.fetchall()
    income_categories = [row for row in categories if row[2] == 'income']
    expense_categories = [row for row in categories if row[2] == 'expense']

    category_filter = request.args.get('category_id', type=int)
    query = """
        SELECT t.id, t.amount, t.type, t.description, t.date,
               a.name, c.name
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        JOIN categories c ON c.id = t.category_id
    """
    params = []

    if category_filter:
        query += " WHERE t.category_id = ?"
        params.append(category_filter)

    query += " ORDER BY t.date DESC"

    c.execute(query, params)
    transactions = c.fetchall()
    conn.close()

    return render_template(
        'index.html',
        transactions=transactions,
        categories=categories,
        income_categories=income_categories,
        expense_categories=expense_categories,
        selected_category_id=category_filter
    )

# -----------------------
# CREATE ACCOUNT
# -----------------------
@app.route('/accounts/create', methods=['GET', 'POST'])
def create_account():
    if request.method == 'POST':
        name = request.form['name']
        type_ = request.form['type']
        balance = int(request.form['initial_balance'])

        conn = sqlite3.connect(dir_db)
        c = conn.cursor()

        c.execute("""
            INSERT INTO accounts (name, type, initial_balance)
            VALUES (?, ?, ?)
        """, (name, type_, balance))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('create_account.html')

# -----------------------
# CREATE CATEGORY
# -----------------------
@app.route('/categories/create', methods=['GET', 'POST'])
def create_category():
    if request.method == 'POST':
        name = request.form['name']
        type_ = request.form['type']

        conn = sqlite3.connect(dir_db)
        c = conn.cursor()

        c.execute("""
            INSERT INTO categories (name, type)
            VALUES (?, ?)
        """, (name, type_))

        conn.commit()
        conn.close()

        return redirect('/')

    return render_template('create_category.html')

# -----------------------
# CREATE TRANSACTION
# -----------------------
@app.route('/transactions/create', methods=['GET', 'POST'])
def create_transaction():
    conn = sqlite3.connect(dir_db)
    c = conn.cursor()

    # Obtener cuentas y categorías
    c.execute("SELECT * FROM accounts")
    accounts = c.fetchall()

    c.execute("SELECT * FROM categories ORDER BY type, name")
    categories = c.fetchall()
    income_categories = [row for row in categories if row[2] == 'income']
    expense_categories = [row for row in categories if row[2] == 'expense']

    if request.method == 'POST':
        account_id = request.form['account_id']
        category_id = request.form['category_id']
        amount = int(request.form['amount'])
        description = request.form['description']
        date = request.form['date']

        amount_type = 'expense' if amount < 0 else 'income'
        amount = abs(amount)

        if amount == 0:
            conn.close()
            return "El monto no puede ser cero"

        c.execute("SELECT type FROM categories WHERE id = ?", (category_id,))
        category_row = c.fetchone()
        if not category_row:
            conn.close()
            return "Categoría inválida"

        c.execute("""
            INSERT INTO transactions 
            (account_id, category_id, amount, type, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (account_id, category_id, amount, amount_type, description, date))

        conn.commit()
        conn.close()

        return redirect('/')

    conn.close()
    return render_template(
        'create_transaction.html',
        accounts=accounts,
        categories=categories,
        income_categories=income_categories,
        expense_categories=expense_categories
    )

# -----------------------
# EDIT TRANSACTION
# -----------------------
@app.route('/transactions/edit/<int:id>', methods=['GET', 'POST'])
def edit_transaction(id):
    conn = sqlite3.connect(dir_db)
    c = conn.cursor()

    c.execute("SELECT id, account_id, category_id, amount, description, date, type FROM transactions WHERE id = ?", (id,))
    transaction = c.fetchone()
    if not transaction:
        conn.close()
        return redirect('/')

    c.execute("SELECT * FROM accounts")
    accounts = c.fetchall()

    c.execute("SELECT * FROM categories ORDER BY type, name")
    categories = c.fetchall()
    income_categories = [row for row in categories if row[2] == 'income']
    expense_categories = [row for row in categories if row[2] == 'expense']

    if request.method == 'POST':
        account_id = request.form['account_id']
        category_id = request.form['category_id']
        amount = int(request.form['amount'])
        description = request.form['description']
        date = request.form['date']

        amount_type = 'expense' if amount < 0 else 'income'
        amount = abs(amount)

        if amount == 0:
            conn.close()
            return "El monto no puede ser cero"

        c.execute("SELECT type FROM categories WHERE id = ?", (category_id,))
        category_row = c.fetchone()
        if not category_row:
            conn.close()
            return "Categoría inválida"

        c.execute("""
            UPDATE transactions
            SET account_id = ?, category_id = ?, amount = ?, type = ?, description = ?, date = ?
            WHERE id = ?
        """, (account_id, category_id, amount, amount_type, description, date, id))

        conn.commit()
        conn.close()
        return redirect('/')

    conn.close()
    return render_template(
        'edit_transaction.html',
        transaction=transaction,
        accounts=accounts,
        income_categories=income_categories,
        expense_categories=expense_categories
    )

# -----------------------
# CHARTS
# -----------------------
@app.route('/charts')
def charts():
    conn = sqlite3.connect(dir_db)
    c = conn.cursor()

    # Obtener todas las cuentas para el selector
    c.execute("SELECT id, name FROM accounts ORDER BY name")
    all_accounts = c.fetchall()
    
    account_filter = request.args.get('account_id', type=int)

    # Gráfica de ingresos y gastos por categoría (todas las categorías)
    if account_filter:
        c.execute("""
            SELECT c.name, c.type, SUM(t.amount)
            FROM transactions t
            JOIN categories c ON c.id = t.category_id
            WHERE t.account_id = ?
            GROUP BY c.id
            ORDER BY c.type, c.name
        """, (account_filter,))
    else:
        c.execute("""
            SELECT c.name, c.type, SUM(t.amount)
            FROM transactions t
            JOIN categories c ON c.id = t.category_id
            GROUP BY c.id
            ORDER BY c.type, c.name
        """)
    category_totals = c.fetchall()
    category_labels = [row[0] for row in category_totals]
    category_amounts = [row[2] if row[2] else 0 for row in category_totals]
    category_types = [row[1] for row in category_totals]

    # Balance de cuentas (con o sin filtro)
    if account_filter:
        c.execute("""
            SELECT a.name,
                   a.initial_balance + COALESCE(SUM(
                       CASE WHEN t.type = 'income' THEN t.amount
                            WHEN t.type = 'expense' THEN -t.amount
                            ELSE 0 END
                   ), 0) as balance
            FROM accounts a
            LEFT JOIN transactions t ON t.account_id = a.id AND a.id = ?
            WHERE a.id = ?
            GROUP BY a.id
        """, (account_filter, account_filter))
    else:
        c.execute("""
            SELECT a.name,
                   a.initial_balance + COALESCE(SUM(
                       CASE WHEN t.type = 'income' THEN t.amount
                            WHEN t.type = 'expense' THEN -t.amount
                            ELSE 0 END
                   ), 0) as balance
            FROM accounts a
            LEFT JOIN transactions t ON t.account_id = a.id
            GROUP BY a.id
        """)
    account_balances = c.fetchall()
    account_labels = [row[0] for row in account_balances]
    account_values = [row[1] for row in account_balances]

    # Movimiento mensual (ingresos vs gastos)
    if account_filter:
        c.execute("""
            SELECT strftime('%Y-%m', date) AS month,
                   SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expense
            FROM transactions
            WHERE account_id = ?
            GROUP BY month
            ORDER BY month
        """, (account_filter,))
    else:
        c.execute("""
            SELECT strftime('%Y-%m', date) AS month,
                   SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END) AS income,
                   SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END) AS expense
            FROM transactions
            GROUP BY month
            ORDER BY month
        """)
    monthly_trends = c.fetchall()
    monthly_labels = [row[0] for row in monthly_trends]
    monthly_income = [row[1] if row[1] else 0 for row in monthly_trends]
    monthly_expense = [row[2] if row[2] else 0 for row in monthly_trends]

    conn.close()

    return render_template(
        'charts.html',
        all_accounts=all_accounts,
        account_filter=account_filter,
        category_totals=category_totals,
        category_labels=category_labels,
        category_amounts=category_amounts,
        category_types=category_types,
        account_balances=account_balances,
        account_labels=account_labels,
        account_values=account_values,
        monthly_trends=monthly_trends,
        monthly_labels=monthly_labels,
        monthly_income=monthly_income,
        monthly_expense=monthly_expense
    )

# -----------------------
# DELETE TRANSACTION
# -----------------------
@app.route('/delete/<int:id>')
def delete(id):
    conn = sqlite3.connect(dir_db)
    c = conn.cursor()

    c.execute("DELETE FROM transactions WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/')

# -----------------------
# BALANCE
# -----------------------
@app.route('/balance')
def balance():
    conn = sqlite3.connect(dir_db)
    c = conn.cursor()

    c.execute("""
        SELECT 
            a.name,
            a.initial_balance +
            COALESCE(SUM(
                CASE 
                    WHEN t.type = 'income' THEN t.amount
                    WHEN t.type = 'expense' THEN -t.amount
                END
            ), 0) as balance
        FROM accounts a
        LEFT JOIN transactions t ON t.account_id = a.id
        GROUP BY a.id
    """)

    balances = c.fetchall()
    conn.close()

    return render_template('balance.html', balances=balances)

# -----------------------
# RUN
# -----------------------
if __name__ == '__main__':
    app.run(debug=True)