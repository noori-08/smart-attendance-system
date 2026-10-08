import os
import uuid
import qrcode

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_qr():
    token = str(uuid.uuid4())

    folder = os.path.join(BASE_DIR, "static", "qr_codes")
    os.makedirs(folder, exist_ok=True)

    path = os.path.join(folder, "current_qr.png")

    img = qrcode.make(token)
    img.save(path)

    return token, path