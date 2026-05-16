FROM python:3.11-slim

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
        build-essential \
        python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step 1: pip + setuptools + wheel upgrade
RUN pip install --upgrade pip setuptools wheel

# Step 2: numpy hore u install (whisper u baahan yahay)
RUN pip install "numpy<2.0"

# Step 3: whisper gaar ahaan install (git source-ka toos ah)
RUN pip install git+https://github.com/openai/whisper.git

# Step 4: Remaining packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Whisper model pre-download
RUN python -c "import whisper; whisper.load_model('base')" || true

CMD ["python", "bot.py"]
