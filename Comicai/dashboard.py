from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, abort, send_file, current_app
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
        name   = request.form.get('name', '').strip()
        prompt = request.form.get('description', '').strip()
        upload = request.files.get('image')

        if not name or not prompt:
            flash('Nazwa i opis są wymagane.')
            return redirect(url_for('dashboard.add_character'))

        try:
            if upload and upload.filename:
                char_id = getImageToImage(name, prompt, upload)
            else:
                char_id = getTextToImage(name, prompt)
        except Exception as exc:
            current_app.logger.exception(exc)
            flash('Coś poszło nie tak przy generowaniu obrazu.')
            return redirect(url_for('dashboard.add_character'))

        return redirect(url_for('dashboard.character_generated',
                                char_id=char_id, prompt=prompt))

    return render_template('dashboard/add_character.html')



@bp.route('/character_generated/<int:char_id>')
@login_required
def character_generated(char_id):
    prompt = request.args.get('prompt', '')

    row = get_db().execute(
        # ▼ switch title → name
        "SELECT id, name FROM character WHERE id = ? AND author_id = ?",
        (char_id, g.user['id'])
    ).fetchone()

    if row is None:
        abort(404)

    return render_template(
        'dashboard/character_generated.html',
        character=row,
        prompt=prompt
    )

@bp.route('/character/<int:char_id>/regenerate', methods=('POST',))
@login_required
def regenerate_character(char_id):
    prompt = request.form.get('prompt', '').strip()
    upload = request.files.get('image')

    # security: ensure user owns the char
    owner = get_db().execute(
        "SELECT 1 FROM character WHERE id = ? AND author_id = ?",
        (char_id, g.user['id'])
    ).fetchone()
    if owner is None:
        abort(404)

    regenerate_character_image(char_id, prompt, upload)
    flash('Obraz zregenerowany.')
    return redirect(url_for('dashboard.character_generated',
                            char_id=char_id, prompt=prompt))

@bp.route('/view_characters')
@login_required
def view_characters():
    rows = get_db().execute(
        "SELECT id, name FROM character WHERE author_id = ? ORDER BY created DESC",
        (g.user['id'],)
    ).fetchall()
    return render_template('dashboard/view_characters.html',
                           characters=rows)

@bp.route("/character/<int:char_id>")
@login_required
def character_detail(char_id):
    row = get_db().execute(
        "SELECT id, name FROM character WHERE id = ? AND author_id = ?",
        (char_id, g.user['id'])
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

@bp.route('/view_comics')
@login_required
def view_comics():
    rows = get_db().execute(
        """
        SELECT c.id,
               c.title,
               (SELECT id
                FROM comic_page
                WHERE comic_id = c.id AND page_number = 1) AS page1_id
        FROM comic AS c
        WHERE c.author_id = ?
        ORDER BY c.created DESC
        """,
        (g.user['id'],)
    ).fetchall()
    return render_template('dashboard/view_comics.html', comics=rows)

@bp.route('/add_comic', methods=('GET', 'POST'))
@login_required
def add_comic():
    db = get_db()

    if request.method == 'GET':
        chars = db.execute(
            "SELECT id, name FROM character WHERE author_id = ?",
            (g.user['id'],)
        ).fetchall()
        return render_template(
            'dashboard/add_comic.html',
            characters=chars
        )

    # POST
    title   = request.form.get('title', '').strip()
    desc    = request.form.get('description', '').strip()
    sel_ids = request.form.getlist('characters')
    upload  = request.files.get('image')

    if not title or not desc:
        flash('Tytuł i opis są wymagane.')
        return redirect(url_for('dashboard.add_comic'))

    # build prompt inc. character names
    if sel_ids:
        placeholders = ','.join('?' * len(sel_ids))
        names = db.execute(
            f"SELECT name FROM character WHERE id IN ({placeholders}) "
            "AND author_id = ?",
            (*sel_ids, g.user['id'])
        ).fetchall()
        chars_string = ', '.join(r['name'] for r in names)
        prompt = f"{desc}. Bohaterowie: {chars_string}"
    else:
        prompt = desc

    comic_id = create_comic_and_first_page(title, prompt, upload)
    flash('Komiks zapisany.')
    return redirect(url_for('dashboard.comic_detail', comic_id=comic_id))

@bp.route('/comic/<int:comic_id>')
@login_required
def comic_detail(comic_id):
    db = get_db()
    head = db.execute(
        "SELECT id, title AS name FROM comic WHERE id = ? AND author_id = ?",
        (comic_id, g.user['id'])
    ).fetchone()
    if head is None:
        abort(404)

    pages = db.execute(
        """
        SELECT id, page_number
        FROM comic_page
        WHERE comic_id = ?
        ORDER BY page_number
        """,
        (comic_id,)
    ).fetchall()

    return render_template(
        'dashboard/comic.html',
        comic=head,
        pages=pages
    )

@bp.route('/comic_page_image/<int:page_id>')
@login_required
def comic_page_image(page_id):
    row = get_db().execute(
        "SELECT image FROM comic_page WHERE id = ?", (page_id,)
    ).fetchone()
    if row is None:
        abort(404)

    return send_file(
        io.BytesIO(row['image']),
        mimetype='image/png'
    )

@bp.route("/comic/<int:comic_id>/add_page", methods=("POST",))
@login_required
def add_page(comic_id):
    db = get_db()

    # confirm user owns the comic
    comic = db.execute(
        "SELECT id FROM comic WHERE id = ? AND author_id = ?",
        (comic_id, g.user["id"])
    ).fetchone()
    if comic is None:
        abort(404)

    prompt  = request.form.get("description", "").strip()
    upload  = request.files.get("image")

    if not prompt:
        flash("Opis / prompt jest wymagany.")
        return redirect(url_for("dashboard.comic_detail", comic_id=comic_id))

    add_page_to_comic(comic_id, prompt, upload)
    flash("Dodano nową stronę.")
    return redirect(url_for("dashboard.comic_detail", comic_id=comic_id))

@bp.route("/comic_page/<int:page_id>/regenerate", methods=("POST",))
@login_required
def regenerate_page(page_id):
    prompt = request.form.get("prompt", "").strip()
    upload = request.files.get("image")

    if not prompt:
        flash("Opis / prompt jest wymagany.")
        # look up parent comic to redirect back
        comic_id = get_db().execute(
            "SELECT comic_id FROM comic_page WHERE id = ?", (page_id,)
        ).fetchone()
        return redirect(url_for("dashboard.comic_detail",
                                comic_id=comic_id["comic_id"]))

    try:
        regenerate_comic_page(page_id, prompt, upload)
        flash("Stronę zregenerowano.")
    except PermissionError:
        abort(404)
    return redirect(request.referrer or url_for("dashboard.view_comics"))

@bp.route("/comic/<int:comic_id>/regenerate_last", methods=("POST",))
@login_required
def regenerate_last(comic_id):
    # security: ensure ownership
    owns = get_db().execute(
        "SELECT 1 FROM comic WHERE id=? AND author_id=?",
        (comic_id, g.user['id'])
    ).fetchone()
    if owns is None:
        abort(404)

    try:
        regenerate_last_page(comic_id)
        flash("Ostatnia strona zregenerowana.")
    except Exception as exc:
        current_app.logger.exception(exc)
        flash("Nie udało się zregenerować strony.")

    return redirect(url_for("dashboard.comic_detail", comic_id=comic_id))

