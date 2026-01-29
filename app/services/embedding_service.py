import hashlib

def embed_text(text: str):
    h = hashlib.sha256(text.encode()).digest()
    return [b / 255 for b in h[:64]]
