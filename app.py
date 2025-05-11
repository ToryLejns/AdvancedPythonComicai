from flask import Flask, render_template, request, redirect, url_for, session, flash

users = {}

app = Flask(__name__)
app.secret_key = 'secret_key'


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if users.get(username) == password:
            session['username'] = username
            return redirect(url_for('dashboard'))
        flash('Błędny login lub hasło.')
    return render_template('login.html', username="Guest")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users:
            flash('Użytkownik już istnieje.')
            return redirect(url_for('register'))
        users[username] = password
        flash('Zarejestrowano pomyślnie. Zaloguj się.')
        return redirect(url_for('login'))
    return render_template('register.html', username="Guest")


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', username=session['username'])


@app.route('/add-character')
def add_character():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('add_character.html', username=session['username'])


@app.route('/view-characters')
def view_characters():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('view_characters.html', username=session['username'])


@app.route('/add-comic')
def add_comic():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('add_comic.html', username=session['username'])


@app.route('/view-comics')
def view_comics():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('view_comics.html', username=session['username'])


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
