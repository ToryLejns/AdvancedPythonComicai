from calendar import error

from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for, abort
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
        name = request.form['name']
        prompt = request.form['description']
        picture = request.files.get("image")
        error = None
        if not name:
            error = 'Name is required!'

        if not prompt:
            error = 'description is required!'

        if picture and picture.filename == "":
            error = 'empty file!'

        if not error:
            if not picture:
                getTextToImage(prompt)
            else:
                getImageToImage(prompt, picture)


    return render_template('dashboard/add_character.html')

@bp.route('/add_comic', methods=('GET', 'POST'))
@login_required
def add_comic():
    return render_template('dashboard/add_comic.html')

@bp.route('/view_characters', methods=('GET', 'POST'))
@login_required
def view_characters():
    return render_template('dashboard/view_characters.html')

@bp.route('/view_comics', methods=('GET', 'POST'))
@login_required
def view_comics():
    return render_template('dashboard/view_comics.html')