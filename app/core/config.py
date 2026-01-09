import os

# 🔐 CHAVE SECRETA (em produção virá do ambiente)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-later")

# 🔏 ALGORITMO JWT (OBRIGATÓRIO)
ALGORITHM = "HS256"

# ⏱️ TEMPO DE EXPIRAÇÃO DO TOKEN (MINUTOS)
ACCESS_TOKEN_EXPIRE_MINUTES = 60

