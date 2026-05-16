FROM python:3.11-slim

# Install ffmpeg (Whisper u baahan yahay)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# MUHIIM: setuptools iyo wheel hore u install (pkg_resources fix)
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Requirements copy & install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bot code copy
COPY bot.py .

# Whisper model pre-download (build time-ka) — "base" model
RUN python -c "import whisper; whisper.load_model('base')" || true

CMD ["python", "bot.py"]
