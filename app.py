from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config['SESSION_PERMANENT'] = False

# ======================================
# DISABLE CACHE
# ======================================

@app.after_request
def disable_cache(response):

    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

    response.headers["Pragma"] = "no-cache"

    response.headers["Expires"] = "0"

    return response

# ======================================
# DATABASE CONNECTION
# ======================================

try:

    db = mysql.connector.connect(

        host=os.environ.get("MYSQLHOST"),

        user=os.environ.get("MYSQLUSER"),

        password=os.environ.get("MYSQLPASSWORD"),

        database=os.environ.get("MYSQLDATABASE"),

        port=int(os.environ.get("MYSQLPORT"))

    )

    cursor = db.cursor(dictionary=True)

    print("Database Connected Successfully")

except Exception as e:

    print("Database Connection Error:", e)
# ======================================
# HOME PAGE
# ======================================

@app.route('/')
def home():
    return render_template('index.html')

# ======================================
# REGISTER
# ======================================

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        username = request.form['username']
        mobile_number = request.form['mobile_number']
        upi_id = request.form['upi_id']
        password = request.form['password']

        # MOBILE VALIDATION

        if len(mobile_number) != 10:

            flash("Mobile Number Must Be 10 Digits")

            return redirect('/register')

        # CHECK USER EXISTS

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE upi_id=%s
            """,
            (upi_id,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            flash("UPI ID Already Exists")

            return redirect('/register')

        # INSERT USER

        cursor.execute(
            """
            INSERT INTO users(

                username,
                mobile_number,
                upi_id,
                password

            )

            VALUES(%s,%s,%s,%s)
            """,

            (
                username,
                mobile_number,
                upi_id,
                password
            )
        )

        db.commit()

        # GET USER ID

        user_id = cursor.lastrowid

        # CREATE WALLET

        cursor.execute(
            """
            INSERT INTO wallets(
                user_id,
                balance
            )

            VALUES(%s,%s)
            """,

            (
                user_id,
                0
            )
        )

        db.commit()

        # CREATE NOTIFICATION

        cursor.execute(
            """
            INSERT INTO notifications(
                user_id,
                message
            )

            VALUES(%s,%s)
            """,

            (
                user_id,
                "Account Created Successfully"
            )
        )

        db.commit()

        flash("Registration Successful")

        return redirect('/login')

    return render_template('register.html')

# ======================================
# LOGIN
# ======================================

# ======================================
# LOGIN
# ======================================

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        upi_id = request.form['upi_id']
        password = request.form['password']

        cursor.execute(
            """
            SELECT *
            FROM users

            WHERE upi_id=%s
            AND password=%s
            """,

            (
                upi_id,
                password
            )
        )

        user = cursor.fetchone()

        # CHECK IF ACCOUNT IS FROZEN

        if user and user['status'] == 'Frozen':

            flash("Your Account Is Frozen By Admin")

            return redirect('/login')

        # NORMAL LOGIN

        if user:

            session['user_id'] = user['user_id']

            session['username'] = user['username']

            flash("Login Successful")

            return redirect('/dashboard')

        else:

            flash("Invalid UPI ID or Password")

            return redirect('/login')

    return render_template('login.html')
# ======================================
# DASHBOARD
# ======================================

# ======================================
# DASHBOARD
# ======================================

@app.route('/dashboard')
def dashboard():

    # CHECK LOGIN

    if 'user_id' not in session:
        return redirect('/login')

    # GET USER BALANCE

    cursor.execute(
        """
        SELECT balance
        FROM wallets
        WHERE user_id=%s
        """,

        (session['user_id'],)
    )

    wallet = cursor.fetchone()

    balance = wallet['balance']

    # ======================================
    # GET ONLY CURRENT USER TRANSACTIONS
    # ======================================

    cursor.execute(
        """
        SELECT

        
            t.transaction_id,

            u1.username AS sender,

            u2.username AS receiver,

            t.amount,

            t.transaction_date,

            t.status

        FROM transactions t

        JOIN users u1
        ON t.sender_id = u1.user_id

        JOIN users u2
        ON t.receiver_id = u2.user_id

        WHERE
        t.sender_id=%s
        OR
        t.receiver_id=%s

        ORDER BY t.transaction_id DESC
        """,

        (
            session['user_id'],
            session['user_id']
        )
    )

    transactions = cursor.fetchall()

    # RENDER PAGE

    return render_template(
        'dashboard.html',
        username=session['username'],
        balance=balance,
        transactions=transactions
    )

# ======================================
# ADD MONEY
# ======================================

@app.route('/add_money', methods=['GET', 'POST'])
def add_money():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        amount = float(request.form['amount'])

        # INSERT TRANSACTION

        cursor.execute(
            """
            INSERT INTO transactions(

                sender_id,
                receiver_id,
                amount,
                status

            )

            VALUES(%s,%s,%s,%s)
            """,

            (
                session['user_id'],
                session['user_id'],
                amount,
                'Deposited'
            )
        )

        db.commit()

        # UPDATE WALLET

        cursor.execute(
            """
            UPDATE wallets

            SET balance = balance + %s

            WHERE user_id=%s
            """,

            (
                amount,
                session['user_id']
            )
        )

        db.commit()

        # ADD NOTIFICATION

        cursor.execute(
            """
            INSERT INTO notifications(
                user_id,
                message
            )

            VALUES(%s,%s)
            """,

            (
                session['user_id'],
                f"Added ₹{amount} to wallet"
            )
        )

        db.commit()

        flash("Money Added Successfully")

        return redirect('/dashboard')

    return render_template('add_money.html')

# ======================================
# SEND MONEY
# ======================================

@app.route('/send_money', methods=['GET', 'POST'])
def send_money():

    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':

        receiver_upi = request.form['receiver_upi']
        amount = float(request.form['amount'])
        if amount >=100000:
            flash("Out of range money")
            return redirect('/send_money')

        # GET RECEIVER

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE upi_id=%s
            """,

            (receiver_upi,)
        )

        receiver = cursor.fetchone()

        if not receiver:

            flash("Receiver Not Found")

            return redirect('/send_money')

        receiver_id = receiver['user_id']

        # CHECK BALANCE

        cursor.execute(
            """
            SELECT balance
            FROM wallets
            WHERE user_id=%s
            """,

            (session['user_id'],)
        )

        wallet = cursor.fetchone()

        if wallet['balance'] < amount:

            flash("Insufficient Balance")

            return redirect('/send_money')

        # INSERT TRANSACTION

        cursor.execute(
            """
            INSERT INTO transactions(

                sender_id,
                receiver_id,
                amount,
                status

            )

            VALUES(%s,%s,%s,%s)
            """,

            (
                session['user_id'],
                receiver_id,
                amount,
                'Success'
            )
        )

        db.commit()

        # DEDUCT SENDER BALANCE

        cursor.execute(
            """
            UPDATE wallets

            SET balance = balance - %s

            WHERE user_id=%s
            """,

            (
                amount,
                session['user_id']
            )
        )

        # ADD RECEIVER BALANCE

        cursor.execute(
            """
            UPDATE wallets

            SET balance = balance + %s

            WHERE user_id=%s
            """,

            (
                amount,
                receiver_id
            )
        )

        db.commit()

        # SENDER NOTIFICATION

        cursor.execute(
            """
            INSERT INTO notifications(
                user_id,
                message
            )

            VALUES(%s,%s)
            """,

            (
                session['user_id'],
                f"Sent ₹{amount} successfully"
            )
        )

        # RECEIVER NOTIFICATION

        cursor.execute(
            """
            INSERT INTO notifications(
                user_id,
                message
            )

            VALUES(%s,%s)
            """,

            (
                receiver_id,
                f"Received ₹{amount}"
            )
        )

        db.commit()

        flash("Money Sent Successfully")

        return redirect('/dashboard')

    return render_template('send_money.html')

# ======================================
# NOTIFICATIONS
# ======================================

@app.route('/notifications')
def notifications():

    if 'user_id' not in session:
        return redirect('/login')

    cursor.execute(
        """
        SELECT *
        FROM notifications

        WHERE user_id=%s

        ORDER BY notification_id DESC
        """,

        (session['user_id'],)
    )

    notifications = cursor.fetchall()

    return render_template(
        'notifications.html',
        notifications=notifications
    )

# ======================================
# TRANSACTION HISTORY
# ======================================

@app.route('/history')
def history():

    if 'user_id' not in session:
        return redirect('/login')

    # GET USER TRANSACTIONS

    # GET ONLY CURRENT USER TRANSACTIONS

# GET ONLY CURRENT USER TRANSACTIONS

    cursor.execute(
        """
        SELECT

            t.transaction_id,

            u1.username AS sender,

            u2.username AS receiver,

            t.amount,

            t.transaction_date,

            t.status

        FROM transactions t

        JOIN users u1
        ON t.sender_id = u1.user_id

        JOIN users u2
        ON t.receiver_id = u2.user_id

        WHERE
        t.sender_id=%s
        OR
        t.receiver_id=%s

        ORDER BY t.transaction_id DESC
        """,

        (
            session['user_id'],
            session['user_id']
        )
    )

    transactions = cursor.fetchall()

    return render_template(
        'history.html',
        transactions=transactions
    )

# ======================================
# LOGOUT
# ======================================

@app.route('/logout')
def logout():

    session.pop('user_id', None)

    session.pop('username', None)

    session.pop('admin', None)

    session.clear()

    flash("Logged Out Successfully")

    return redirect('/login')
# ======================================
# ADMIN LOGIN
# ======================================

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():

    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        cursor.execute(
            """
            SELECT *
            FROM admins

            WHERE username=%s
            AND password=%s
            """,

            (
                username,
                password
            )
        )

        admin = cursor.fetchone()

        if admin:

            session['admin'] = username

            flash("Admin Login Successful")

            return redirect('/admin_dashboard')

        else:

            flash("Invalid Admin Credentials")

            return redirect('/admin_login')

    return render_template('admin_login.html')

# ======================================
# ADMIN DASHBOARD
# ======================================

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'admin' not in session:
        return redirect('/admin_login')

    # GET USERS

    cursor.execute(
        """
        SELECT *
        FROM users

        ORDER BY user_id DESC
        """
    )

    users = cursor.fetchall()

    # GET TRANSACTIONS

    cursor.execute(
        """
        SELECT

            t.transaction_id,

            u1.username AS sender,

            u2.username AS receiver,

            t.amount,

            t.transaction_date,

            t.status

        FROM transactions t

        JOIN users u1
        ON t.sender_id=u1.user_id

        JOIN users u2
        ON t.receiver_id=u2.user_id

        ORDER BY t.transaction_id DESC
        """
    )

    transactions = cursor.fetchall()

    return render_template(
        'admin_dashboard.html',
        users=users,
        transactions=transactions
    )
# ======================================
# FREEZE ACCOUNT
# ======================================

@app.route('/freeze_user/<int:user_id>')
def freeze_user(user_id):

    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute(
        """
        UPDATE users

        SET status='Frozen'

        WHERE user_id=%s
        """,

        (user_id,)
    )

    db.commit()

    flash("User Account Frozen")

    return redirect('/admin_dashboard')

# ======================================
# UNFREEZE ACCOUNT
# ======================================

@app.route('/unfreeze_user/<int:user_id>')
def unfreeze_user(user_id):

    if 'admin' not in session:
        return redirect('/admin_login')

    cursor.execute(
        """
        UPDATE users

        SET status='Active'

        WHERE user_id=%s
        """,

        (user_id,)
    )

    db.commit()

    flash("User Account Activated")

    return redirect('/admin_dashboard')

# ======================================
# DELETE USER
# ======================================

# ======================================
# DELETE USER
# ======================================

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):

    if 'admin' not in session:
        return redirect('/admin_login')

    # DELETE USER TRANSACTIONS

    cursor.execute(
        """
        DELETE FROM transactions

        WHERE sender_id=%s
        OR receiver_id=%s
        """,

        (
            user_id,
            user_id
        )
    )

    # DELETE USER NOTIFICATIONS

    cursor.execute(
        """
        DELETE FROM notifications

        WHERE user_id=%s
        """,

        (user_id,)
    )

    # DELETE USER WALLET

    cursor.execute(
        """
        DELETE FROM wallets

        WHERE user_id=%s
        """,

        (user_id,)
    )

    # DELETE USER

    cursor.execute(
        """
        DELETE FROM users

        WHERE user_id=%s
        """,

        (user_id,)
    )

    db.commit()

    flash("User Deleted Successfully")

    return redirect('/admin_dashboard')
# ======================================
# RUN APP
# ======================================

if __name__ == '__main__':
    app.run(debug=True)