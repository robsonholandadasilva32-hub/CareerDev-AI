translations = {
    "pt": {
        "login_title": "Máquinas ampliam o potencial humano",
        "login_button": "Entrar com segurança"
    },
    "en": {
        "login_title": "Machines amplify human potential",
        "login_button": "Secure Login"
    },
    "es": {
        "login_title": "Las máquinas amplían el potencial humano",
        "login_button": "Acceso seguro"
    }
}

def t(lang: str, key: str):
    return translations.get(lang, translations["pt"]).get(key, key)

