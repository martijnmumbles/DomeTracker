import requests
from django.conf import settings


def generate_meme(image_id, texts):
    formatted_text = dict(
        [("boxes[" + str(i) + "][text]", texts[i]) for i in range(0, len(texts))]
    )
    headers = {
        "template_id": str(image_id),
        "username": "martijnmumbles",
        "password": settings.IMGFLIP_PW,
    }
    headers.update(formatted_text)
    meme = requests.post("https://api.imgflip.com/caption_image", params=headers)
    return meme.json()
