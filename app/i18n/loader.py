import json
from pathlib import Path

BASE_PATH = Path(__file__).parent

_cache = {}


def get_texts(lang: str):
    if lang in _cache:
        return _cache[lang]

    file = BASE_PATH / f"{lang}.json"

    if not file.exists():
        file = BASE_PATH / "pt.json"

    with open(file, encoding="utf-8") as f:
        texts = json.load(f)
        _cache[lang] = texts
        return texts


class I18nLoader:
    def get_text(self, lang: str):
        return get_texts(lang)

i18n = I18nLoader()
