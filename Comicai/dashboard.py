

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)

from flaskr.auth import login_required
from flaskr.characterClient import getCharacter
from flaskr.db import get_db

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    db = get_db()
    chracters = db.execute(
        'SELECT p.id, title, image, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()
    return render_template('dashboard.index.html', chracters=chracters)

@bp.route('/generateCharacter', methods=('GET', 'POST'))
@login_required
def generateCharacter():
    if request.method == 'POST':
        title = request.form['title']
        prompt = request.form['prompt']
        image = getCharacter(prompt)
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, image, author_id)'
                ' VALUES (?, ?, ?)',
                (title, image, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')