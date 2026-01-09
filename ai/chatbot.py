def simple_ai_response(user_message: str) -> str:
    msg = user_message.lower()

    if "carreira" in msg:
        return "Sua carreira é um sistema em evolução. Pequenas decisões consistentes geram grandes resultados."

    if "segurança" in msg:
        return "Sua sessão é protegida. Nada é armazenado sem seu consentimento."

    if "linguagens" in msg:
        return "Rust, Go e Zig crescem porque resolvem problemas reais de segurança e performance."

    if "ia" in msg:
        return "IA não substitui pessoas. Ela amplia capacidades humanas."

    return "Posso ajudar com carreira, segurança ou aprendizado técnico."


def contextual_response(step: str, lang: str = "pt") -> str:
    responses = {
        "login_email": {
            "pt": "Agora pedimos seu e-mail. Ele serve apenas para identificar você.",
            "en": "Now we ask for your email. It is only used to identify you.",
            "es": "Ahora pedimos su correo. Solo se usa para identificarle."
        },
        "login_password": {
            "pt": "Digite sua senha. Ela é protegida e nunca fica visível.",
            "en": "Enter your password. It is encrypted and never visible.",
            "es": "Ingrese su contraseña. Está protegida y nunca es visible."
        },
        "2fa_reminder": {
            "pt": "Digite o código temporário enviado para você.",
            "en": "Enter the temporary code sent to you.",
            "es": "Ingrese el código temporal enviado."
        }
    }

    return responses.get(step, {}).get(lang, "")

