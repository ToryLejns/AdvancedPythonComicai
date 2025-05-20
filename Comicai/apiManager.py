"""
apiManager.py  –  production version
Replaces the old in-process mockups with real calls to the LitServe
diffusion endpoint.

The public helpers keep exactly the same signatures the dashboard
already uses:

    getTextToImage(name, prompt)            -> char_id
    getImageToImage(name, prompt, upload)   -> char_id
    create_comic_and_first_page(...)
    add_page_to_comic(...)
    regenerate_character_image(...)

If the HTTP call fails we raise, letting the route flash an error and
re-render the form (already handled in dashboard.py).
"""
from datetime import datetime
import io
import requests
from PIL import Image
from flask import g, current_app

from Comicai.blobUtils import pil_image_to_blob
from Comicai.db        import get_db

# -----------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------
GEN_URL = (
    "https://8002-01jvj363s7azr27zgtxpkpce2x.cloudspaces.litng.ai/generate"
)  # ← centralised so you can swap env-driven later


# -----------------------------------------------------------------------
# LOW-LEVEL HTTP WRAPPER
# -----------------------------------------------------------------------
def _call_generation_api(prompt: str, pil_img: Image.Image | None = None) -> Image.Image:
    """
    Talk to the LitServe endpoint.  If *pil_img* is None we do a pure
    txt-to-img; otherwise img-to-img.

    Raises requests.HTTPError on non-200 so the caller can handle it.
    """
    files: dict[str, tuple] = {"prompt": (None, prompt)}
    if pil_img is not None:
        buf = io.BytesIO()
        pil_img.save(buf, format="PNG")
        buf.seek(0)
        files["image"] = ("source.png", buf, "image/png")

    r = requests.post(GEN_URL, files=files, timeout=180)
    r.raise_for_status()  # will raise HTTPError for 4xx/5xx

    return Image.open(io.BytesIO(r.content)).convert("RGB")


# -----------------------------------------------------------------------
# PUBLIC HELPERS  —  CHARACTER
# -----------------------------------------------------------------------
def getTextToImage(name: str, prompt: str) -> int:
    img = _call_generation_api(prompt)
    return _store_character(name, prompt, img)


def getImageToImage(name: str, prompt: str, upload_fs) -> int:
    base_img = Image.open(upload_fs.stream).convert("RGB")
    img = _call_generation_api(prompt, base_img)
    return _store_character(name, prompt, img)


def regenerate_character_image(char_id: int, prompt: str, upload_fs=None) -> None:
    base_img = None
    if upload_fs and upload_fs.filename:
        base_img = Image.open(upload_fs.stream).convert("RGB")

    img = _call_generation_api(prompt, base_img)

    db = get_db()
    db.execute(
        """
        UPDATE character
        SET image=?, prompt=?, regen_cnt = regen_cnt + 1, created=?
        WHERE id=? AND author_id=?
        """,
        (
            pil_image_to_blob(img),
            prompt,
            datetime.utcnow(),
            char_id,
            g.user["id"],
        ),
    )
    db.commit()


def _store_character(name: str, prompt: str, pil_img: Image.Image) -> int:
    blob = pil_image_to_blob(pil_img)
    db = get_db()
    cur = db.execute(
        """
        INSERT INTO character (author_id, name, prompt, image, created)
        VALUES (?, ?, ?, ?, ?)
        """,
        (g.user["id"], name, prompt, blob, datetime.utcnow()),
    )
    db.commit()
    return cur.lastrowid


# -----------------------------------------------------------------------
# PUBLIC HELPERS —  COMICS
# -----------------------------------------------------------------------
def create_comic_and_first_page(title: str, prompt: str, upload_fs=None) -> int:
    base_img = None
    if upload_fs and upload_fs.filename:
        base_img = Image.open(upload_fs.stream).convert("RGB")

    page_img = _call_generation_api(prompt, base_img)
    page_blob = pil_image_to_blob(page_img)

    db = get_db()
    cur = db.execute(
        "INSERT INTO comic (author_id, title, created) VALUES (?, ?, ?)",
        (g.user["id"], title, datetime.utcnow()),
    )
    comic_id = cur.lastrowid

    db.execute(
        """INSERT INTO comic_page (comic_id, page_number, image, prompt, created)
           VALUES (?, 1, ?, ?, ?)""",
        (comic_id, page_blob, prompt, datetime.utcnow()),
    )
    db.commit()
    return comic_id


def add_page_to_comic(comic_id: int, prompt: str, upload_fs=None) -> int:
    base_img = None
    if upload_fs and upload_fs.filename:
        base_img = Image.open(upload_fs.stream).convert("RGB")
    else:
        # use last page as base
        row = get_db().execute(
            "SELECT image FROM comic_page WHERE comic_id=? ORDER BY page_number DESC LIMIT 1",
            (comic_id,),
        ).fetchone()
        if row:
            base_img = Image.open(io.BytesIO(row["image"])).convert("RGB")

    new_img = _call_generation_api(prompt, base_img)
    blob = pil_image_to_blob(new_img)

    db = get_db()
    next_no = (
        db.execute(
            "SELECT COALESCE(MAX(page_number),0)+1 FROM comic_page WHERE comic_id=?",
            (comic_id,),
        )
        .fetchone()[0]
    )

    cur = db.execute(
        "INSERT INTO comic_page (comic_id, page_number, image, prompt, created) "
        "VALUES (?, ?, ?, ?, ?)",
        (comic_id, next_no, blob, prompt, datetime.utcnow()),
    )
    db.commit()
    return cur.lastrowid

def regenerate_comic_page(page_id: int, prompt: str, upload_fs=None) -> None:
    """
    Overwrite the image for an existing comic_page row.
    Keeps page_number; bumps `created` timestamp.
    """
    db = get_db()

    # verify ownership & fetch comic_id (for base img fallback if needed)
    meta = db.execute(
        """SELECT comic_id
             FROM comic_page
            JOIN comic ON comic_page.comic_id = comic.id
            WHERE comic_page.id = ? AND comic.author_id = ?""",
        (page_id, g.user["id"])
    ).fetchone()
    if meta is None:
        raise PermissionError("page not found or not yours")

    base_img = None
    if upload_fs and upload_fs.filename:
        base_img = Image.open(upload_fs.stream).convert("RGB")

    new_img = _call_generation_api(prompt, base_img)
    blob = pil_image_to_blob(new_img)

    db.execute(
        """UPDATE comic_page
              SET image   = ?,
                  created = ?
            WHERE id = ?""",
        (blob, datetime.utcnow(), page_id),
    )
    db.commit()

def regenerate_last_page(comic_id: int) -> None:
    """
    Re-generate only the newest page, using its stored prompt and
    feeding the old image as base.
    """
    db = get_db()
    row = db.execute(
        """SELECT id, prompt, image
             FROM comic_page
            WHERE comic_id = ?
            ORDER BY page_number DESC
            LIMIT 1""",
        (comic_id,)
    ).fetchone()

    if row is None:
        raise ValueError("Comic has no pages")

    old_img  = Image.open(io.BytesIO(row["image"])).convert("RGB")
    prompt   = row["prompt"]
    new_img  = _call_generation_api(prompt, old_img)
    blob     = pil_image_to_blob(new_img)

    db.execute(
        "UPDATE comic_page SET image=?, created=? WHERE id=?",
        (blob, datetime.utcnow(), row["id"]),
    )
    db.commit()
