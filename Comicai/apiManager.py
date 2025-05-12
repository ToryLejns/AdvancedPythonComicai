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

def getTextToImage(title: str, prompt: str) -> int:
    img  = _mock_text_to_image_api(prompt)
    blob = pil_image_to_blob(img)

    db  = get_db()
    cur = db.execute(
        """
        INSERT INTO character (author_id, title, image, created)
        VALUES (?, ?, ?, ?)
        """,
        (g.user["id"], title, blob, datetime.utcnow()),
    )
    db.commit()
    return cur.lastrowid



def getImageToImage(title: str, prompt: str, file_storage) -> int:
    uploaded_img = Image.open(file_storage.stream).convert("RGB")
    img  = _mock_image_to_image_api(prompt, uploaded_img)
    blob = pil_image_to_blob(img)

    db  = get_db()
    cur = db.execute(
        """
        INSERT INTO character (author_id, title, image, created)
        VALUES (?, ?, ?, ?)
        """,
        (g.user["id"], title, blob, datetime.utcnow()),
    )
    db.commit()
    return cur.lastrowid