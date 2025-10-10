# Imagem base leve com Python 3.11
FROM python:3.11-slim

# Diretório de trabalho dentro do container
WORKDIR /app

# Evita que o Python gere arquivos .pyc e garante saída de log imediata
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia os arquivos de dependência
COPY requirements.txt .

# Instala dependências Python (com segurança e sem cache)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir cryptography gunicorn pymysql

# Copia todo o código-fonte do backend
COPY . .

# Porta exposta (para o gunicorn)
EXPOSE 5000

# Comando padrão — o docker-compose substitui por um com espera de MySQL
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
