
import requests
import base64
from io import BytesIO
from PIL import Image

def getCharacter(prompt):

    # Use the provided prompt, or fall back to the default prompt
    prompt_text = prompt

    # Prepare the request data with your prompt
    data = {
        "prompt": prompt_text
    }

    # Send a request to your LitServe server
    response = requests.post("https://8000-01jsyntbbd3k8fdpxb9xqph66x.cloudspaces.litng.ai/predict", json=data)

    # Get the Base64-encoded image string from the response
    img_str = response.json().get("image")

    if img_str:
        # Decode the Base64 string to bytes
        img_bytes = base64.b64decode(img_str)

        # Convert bytes data to PIL Image
        img = Image.open(BytesIO(img_bytes))

        return img
    else:
        print("No image data found.")