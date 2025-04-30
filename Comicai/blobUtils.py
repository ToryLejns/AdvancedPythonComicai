from io import BytesIO

from PIL import Image


def pil_image_to_blob(pil_image):
    """Converts a PIL Image to bytes (blob) for saving into a database."""
    img_byte_arr = BytesIO()
    pil_image.save(img_byte_arr, format='PNG')  # or 'JPEG' depending on your needs
    img_byte_arr = img_byte_arr.getvalue()
    return img_byte_arr

def blob_to_pil_image(blob_data):
    """Converts blob data from database back to a PIL Image."""
    img_byte_arr = BytesIO(blob_data)
    img = Image.open(img_byte_arr)
    return img