import json
from pathlib import Path

BASE_PATH = Path(__file__).parent

def get_texts(lang: str):
    file = BASE_PATH / f"{lang}.json"

    if not file.exists():
        file = BASE_PATH / "pt.json"

    with open(file, encoding="utf-8") as f:
        return json.load(f)

