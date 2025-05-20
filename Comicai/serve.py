from fastapi import FastAPI, UploadFile, File, Form
from starlette.responses import StreamingResponse
from PIL import Image
from io import BytesIO
import generator
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Stable Diffusion API"}

@app.post("/generate")
async def generate(prompt: str = Form(...), image: UploadFile = File(None)):
    if image:
        image_bytes = await image.read()
        image_pil = Image.open(BytesIO(image_bytes)).convert("RGB")
        image_pil = image_pil.resize((768, 512))
        mode = "img2img"
    else:
        image_pil = None
        mode = "text2image"

    result = generator.generate_image(mode, prompt, image_pil)
    return StreamingResponse(result, media_type="image/png")

uvicorn.run(app, host="0.0.0.0", port=8002)
