FROM python:3.10-slim

WORKDIR /app

ENV PYTHONPATH="/app"

# 🧩 Systemabhängigkeiten + deutsche Locale vorbereiten
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    locales \
    libffi-dev \
    libpq-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    libjpeg-dev \
    zlib1g-dev && \
    locale-gen de_DE.UTF-8 && \
    rm -rf /var/lib/apt/lists/*

# 🌍 Manuell Umgebungsvariablen setzen (statt update-locale)
ENV LANG=de_DE.UTF-8
ENV LANGUAGE=de_DE:de
ENV LC_ALL=de_DE.UTF-8

# 📦 Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 💾 App-Code kopieren
COPY . .

EXPOSE 5000

CMD ["python", "app/app.py"]
