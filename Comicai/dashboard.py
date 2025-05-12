from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, abort, send_file
)

from Comicai.auth import login_required
from Comicai.blobUtils import pil_image_to_blob
from Comicai.db import get_db
from Comicai.apiManager import *

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@login_required
def index():
    db = get_db()

    return render_template('dashboard/dashboard.html')

@bp.route('/add_character', methods=('GET', 'POST'))
@login_required
def add_character():
    if request.method == 'POST':
        title = request.form['name']  # Nazwa postaci
        prompt = request.form['description']  # Opis / diffusion prompt
        picture = request.files.get('image')

        error = None
        if not title:
            error = 'Nazwa postaci jest wymagana.'
        elif not prompt:
            error = 'Opis jest wymagany.'
        elif picture and picture.filename == '':
            error = 'Wybrano pusty plik.'

        if error:
            flash(error)
            return render_template('dashboard/add_character.html')

        # --- call the right helper -------------------------------------------------
        if picture:
            char_id = getImageToImage(title, prompt, picture)
        else:
            char_id = getTextToImage(title, prompt)
        # ----------------------------------------------------------------------------

        flash(f'Dodano postać (id={char_id}).')
        return redirect(url_for('dashboard.view_characters'))

    return render_template('dashboard/add_character.html')

@bp.route('/add_comic', methods=('GET', 'POST'))
@login_required
def add_comic():
    return render_template('dashboard/add_comic.html')

@bp.route('/view_characters', methods=('GET', 'POST'))
@login_required
def view_characters():
    rows = get_db().execute(
        """
        SELECT id, title
        FROM   character
        WHERE  author_id = ?
        ORDER  BY created DESC
        """,
        (g.user["id"],)
    ).fetchall()

    return render_template(
        "dashboard/view_characters.html",
        characters=rows
    )

@bp.route("/character/<int:char_id>")
@login_required
def character_detail(char_id):
    row = get_db().execute(
        """
        SELECT id, title       AS name
        FROM   character
        WHERE  id = ? AND author_id = ?
        """,
        (char_id, g.user["id"])
    ).fetchone()

    if row is None:
        abort(404)

    return render_template(
        "dashboard/character.html",
        character=row        # row[name] and row[id] in template
    )

@bp.route("/character_image/<int:char_id>")
@login_required
def character_image(char_id):
    row = get_db().execute(
        """
        SELECT image
        FROM   character
        WHERE  id = ? AND author_id = ?
        """,
        (char_id, g.user["id"])
    ).fetchone()

    if row is None:
        abort(404)

    # row["image"] is the BLOB we stored; wrap it so send_file can stream it
    return send_file(
        io.BytesIO(row["image"]),
        mimetype="image/png"      # our mock API returns PNG-compatible data
    )

@bp.route('/view_comics', methods=('GET', 'POST'))
@login_required
def view_comics():
    return render_template('dashboard/view_comics.html')