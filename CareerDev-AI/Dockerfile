FROM python:3.12-slim

# 1. Configurações de Ambiente (Melhora logs e performance)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 2. Instala dependências do sistema
# netcat-openbsd é usado para aguardar o banco de dados
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt .
# --no-cache-dir reduz o tamanho da imagem final
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Documentação)
EXPOSE 8000

# 3. O Comando de Inicialização Robusto
# - Usa 'sh -c' explicitamente para garantir que a variável ${PORT} funcione
# - A flag --workers 1 é mantida para proteger a memória do TensorFlow
CMD sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"
