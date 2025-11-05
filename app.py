from flask import Flask, render_template, request, redirect, url_for, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
import psycopg2

# --- HARD-CODED CREDENTIALS ---
DATABASE_URL = "postgresql://databases_7cq3_user:75pEHmpS58nUW55ENsADzTSjlWqjCEuZ@dpg-d45gmk8dl3ps738dclm0-a.singapore-postgres.render.com/databases_7cq3"

SECRET_KEY = "super_secret_for_demo"  # change for production

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Connect to DB
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Create tables if they don’t exist
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT now()
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS canvas (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    content TEXT
);
""")
conn.commit()

# --- User class for Flask-Login ---
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    cur.execute("SELECT id, username, password FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    if row:
        return User(*row)
    return None
@app.route("/netflixclone")
def shownetflix():
    return render_template("netflixv2/index.html")
@app.route("/collegenotes")
def showcollegenotes():
    return render_template("collegenotes/index.html")
# --- Register route ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        # hash the password at registration time
        hashed_password = bcrypt.generate_password_hash(
            request.form['password']
        ).decode('utf-8')
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                        (username, hashed_password))
            conn.commit()
            flash('Registration successful. Please log in.')
            return redirect(url_for('login'))
        except psycopg2.Error:
            conn.rollback()
            flash('Username already exists.')
    return render_template('register.html')

# --- Login route ---
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur.execute("SELECT id, username, password FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        # check hash properly
        if row and bcrypt.check_password_hash(row[2], password):
            user = User(*row)
            login_user(user)
            return redirect(url_for('canvas_page'))
        flash('Invalid credentials')
    return render_template('login.html')

# --- Canvas page ---
@app.route('/canvas', methods=['GET', 'POST'])
@login_required
def canvas_page():
    if request.method == 'POST':
        content = request.form['content']
        # check if user already has a canvas entry
        cur.execute("SELECT id FROM canvas WHERE user_id=%s", (current_user.id,))
        if cur.fetchone():
            cur.execute("UPDATE canvas SET content=%s WHERE user_id=%s",
                        (content, current_user.id))
        else:
            cur.execute("INSERT INTO canvas (user_id, content) VALUES (%s, %s)",
                        (current_user.id, content))
        conn.commit()
        flash('Saved!')
    cur.execute("SELECT content FROM canvas WHERE user_id=%s", (current_user.id,))
    row = cur.fetchone()
    content = row[0] if row else ''
    return render_template('canvas.html', content=content)

# --- Logout ---
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
