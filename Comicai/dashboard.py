

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, abort
)

from Comicai.auth import login_required
from Comicai.blobUtils import pil_image_to_blob
from Comicai.characterClient import getCharacter
from Comicai.db import get_db

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    db = get_db()
    # chracters = db.execute(
    #     'SELECT p.id, title, image, created, author_id, username'
    #     ' FROM character p JOIN user u ON p.author_id = u.id'
    #     ' ORDER BY created DESC'
    # ).fetchall()
    #
    # img = get_img(1)

    return render_template('dashboard/index.html')

@bp.route('/generateCharacter', methods=('GET', 'POST'))
@login_required
def generateCharacter():
    if request.method == 'POST':
        # title = request.form['title']
        # prompt = request.form['prompt']
        error = None

        # image = getCharacter(prompt)

        # imageBinary = pil_image_to_blob(image)

        # if not title:
        #     error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            # db = get_db()
            # db.execute(
            #     'INSERT INTO character (title, image, author_id)'
            #     ' VALUES (?, ?, ?)',
            #     ("title", imageBinary, g.user['id'])
            # )
            # db.commit()
            return redirect(url_for('dashboard/index.html'))

    return render_template('dashboard/generateCharacter.html')

def get_img(id, check_author=True):
    img = get_db().execute(
        'SELECT p.id, title, image, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if img is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and img['author_id'] != g.user['id']:
        abort(403)

    return img