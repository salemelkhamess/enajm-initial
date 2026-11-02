FROM python:3.12-slim

# Empêche Python de buffer les logs (important pour Docker)
ENV PYTHONUNBUFFERED=1

WORKDIR /app-scolarite

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y \
    gcc \
    pkg-config \
    default-libmysqlclient-dev \
    libpq-dev \
    libcairo2 \
    libgl1 \
    tesseract-ocr \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copier requirements en premier (optimisation cache Docker)
COPY requirements.txt .

# Upgrade pip + installation dépendances Python
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copier tout le projet
COPY . .

# Exposer le port Django
EXPOSE 8998

# Commande de lancement
CMD ["python", "manage.py", "runserver", "0.0.0.0:8998"]
