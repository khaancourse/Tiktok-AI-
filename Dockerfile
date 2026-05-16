# Isticmaal official Python image oo ku salaysan Alpine (Alpine way yar tahay)
FROM python:3.9-slim-buster

# Deji working directory-ga gudaha container-ka
WORKDIR /app

# Ku rakib system dependencies-ka looga baahan yahay yt-dlp iyo ffmpeg
# yt-dlp iyo ffmpeg-python waxay u baahan karaan ffmpeg system-ka
RUN apt-get update && apt-get install -y \
    ffmpeg \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Nuqul ka samee requirements.txt si hore loo rakibo dependencies-ka
# Tani waxay caawisaa in cache-ka la isticmaalo haddii requirements aysan isbeddelin
COPY requirements.txt .

# Ku rakib Python dependencies-ka
RUN pip install --no-cache-dir -r requirements.txt

# Nuqul ka samee code-kaaga application-ka ah oo dhan
COPY . .

# Muuji dekedda uu app-kaagu ku shaqaynayo
# Tani waxay muhiim u tahay health check-ka Koyeb
EXPOSE 8000

# Qeex command-ka lagu shaqaysiinayo app-kaaga
# Health check server-ka iyo bot-ka waxay ka bilaabanayaan isla Python script
CMD ["python", "telegram_tiktok_bot.py"]
