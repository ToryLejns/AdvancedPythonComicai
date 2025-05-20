import io
import random
from datetime import datetime

from flask import g
from PIL import Image

from Comicai.blobUtils import pil_image_to_blob
from Comicai.db import get_db


# ---------------------------------------------------------------------------
# MOCK “APIs” – replace these two functions with real HTTP calls later
# ---------------------------------------------------------------------------

def _mock_text_to_image_api(prompt: str) -> Image.Image:
    """
    Return a plain RGB square – colour derived from prompt hash.
    Acts as a stand-in for a diffusion model endpoint.
    """
    seed = hash(prompt) & 0xFFFFFF
    colour = ((seed >> 16) & 0xFF, (seed >> 8) & 0xFF, seed & 0xFF)
    return Image.new("RGB", (512, 512), colour)


def _mock_image_to_image_api(prompt: str, source_img: Image.Image) -> Image.Image:
    """
    Very cheap “edit”: draw the prompt text in the top-left corner.
    Keeps the demo predictable while proving the round-trip works.
    """
    edited = source_img.copy().convert("RGBA")
    return edited  # real implementation would call LitServe


# ---------------------------------------------------------------------------
# PUBLIC FUNCTIONS USED BY THE DASHBOARD
# ---------------------------------------------------------------------------

def getTextToImage(name: str, prompt: str) -> int:
    img  = _mock_text_to_image_api(prompt)
    blob = pil_image_to_blob(img)

    db  = get_db()
    cur = db.execute(
        """INSERT INTO character
           (author_id, name, prompt, image, created)
           VALUES (?, ?, ?, ?, ?)""",
        (g.user['id'], name, prompt, blob, datetime.utcnow()),
    )
    db.commit()
    return cur.lastrowid


def getImageToImage(name: str, prompt: str, upload) -> int:
    base = Image.open(upload.stream).convert("RGB")
    img  = _mock_image_to_image_api(prompt, base)
    blob = pil_image_to_blob(img)

    db  = get_db()
    cur = db.execute(
        """INSERT INTO character
           (author_id, name, prompt, image, created)
           VALUES (?, ?, ?, ?, ?)""",
        (g.user['id'], name, prompt, blob, datetime.utcnow()),
    )
    db.commit()
    return cur.lastrowid


def create_comic_and_first_page(title: str, prompt: str, upload=None) -> int:
    db = get_db()

    # decide which API to use
    if upload:
        base_img  = Image.open(upload.stream).convert("RGB")
        page_img  = _mock_image_to_image_api(prompt, base_img)
    else:
        page_img  = _mock_text_to_image_api(prompt)

    page_blob = pil_image_to_blob(page_img)

    # --- comic header (NO image column) ------------------------------
    cur = db.execute(
        "INSERT INTO comic (author_id, title, created) VALUES (?, ?, ?)",
        (g.user["id"], title, datetime.utcnow()),
    )
    comic_id = cur.lastrowid

    # --- page 1 -------------------------------------------------------
    db.execute(
        "INSERT INTO comic_page (comic_id, page_number, image, created) "
        "VALUES (?, 1, ?, ?)",
        (comic_id, page_blob, datetime.utcnow()),
    )

    db.commit()
    return comic_id

def add_page_to_comic(comic_id: int, prompt: str, upload=None) -> int:
    """
    Append a page.  If *upload* is None, use the previous page of
    this comic as the base image.
    """
    db = get_db()

    # ── determine the source image ───────────────────────────────────
    if upload and upload.filename:
        # user-supplied base
        base_img = Image.open(upload.stream).convert("RGB")
        result_img = _mock_image_to_image_api(prompt, base_img)

    else:
        # find last existing page (if any)
        row = db.execute(
            """SELECT image
               FROM   comic_page
               WHERE  comic_id = ?
               ORDER  BY page_number DESC
               LIMIT  1""",
            (comic_id,)
        ).fetchone()

        if row:
            prev_img   = Image.open(io.BytesIO(row["image"])).convert("RGB")
            result_img = _mock_image_to_image_api(prompt, prev_img)
        else:
            # shouldn’t happen, but fall back gracefully
            result_img = _mock_text_to_image_api(prompt)

    blob = pil_image_to_blob(result_img)

    # ── next page number ─────────────────────────────────────────────
    next_num = db.execute(
        "SELECT COALESCE(MAX(page_number), 0) + 1 AS n "
        "FROM comic_page WHERE comic_id = ?",
        (comic_id,)
    ).fetchone()["n"]

    cur = db.execute(
        """INSERT INTO comic_page (comic_id, page_number, image, created)
           VALUES (?, ?, ?, ?)""",
        (comic_id, next_num, blob, datetime.utcnow()),
    )
    db.commit()
    return cur.lastrowid

def regenerate_character_image(char_id: int, prompt: str, upload=None) -> None:
    if upload and upload.filename:
        base = Image.open(upload.stream).convert("RGB")
        new  = _mock_image_to_image_api(prompt, base)
    else:
        new  = _mock_text_to_image_api(prompt)

    blob = pil_image_to_blob(new)

    db = get_db()
    db.execute(
        """UPDATE character
              SET image     = ?,
                  prompt    = ?,
                  regen_cnt = regen_cnt + 1,
                  created   = ?
            WHERE id = ?""",
        (blob, prompt, datetime.utcnow(), char_id),
    )
    db.commit()