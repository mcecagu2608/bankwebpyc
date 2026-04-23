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

    c.execute("SELECT * FROM categories")
    categories = c.fetchall()

    if request.method == 'POST':
        account_id = request.form['account_id']
        category_id = request.form['category_id']
        amount = int(request.form['amount'])
        description = request.form['description']
        date = request.form['date']

        c.execute("SELECT type FROM categories WHERE id = ?", (category_id,))
        category_row = c.fetchone()
        if not category_row:
            conn.close()
            return "Categoría inválida"

        type_ = category_row[0]

        # Validación básica
        if amount <= 0:
            conn.close()
            return "El monto debe ser positivo"

        c.execute("""
            INSERT INTO transactions 
            (account_id, category_id, amount, type, description, date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (account_id, category_id, amount, type_, description, date))

        conn.commit()
        conn.close()

        return redirect('/')

    conn.close()
    return render_template(
        'create_transaction.html',
        accounts=accounts,
        categories=categories
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