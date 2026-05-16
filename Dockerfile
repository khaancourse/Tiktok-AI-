# Isticmaal official Python image oo ku salaysan Debian Bullseye.
# Bullseye (Debian 11) waa nooc ka cusub "Buster" oo kaydadkiisu waa firfircoon yihiin.
# Python 3.9 waxaan u haynaa sababtoo ah taasi waxaad ku bilowday, laakiin waxaad u beddeli kartaa 3.10 ama 3.11.
FROM python:3.9-slim-bullseye

# Deji working directory-ga gudaha container-ka
WORKDIR /app

# Ku rakib system dependencies-ka looga baahan yahay yt-dlp iyo ffmpeg.
# Isticmaal "--no-install-recommends" si aad u yareyso cabbirka image-ka.
# "apt-get clean" iyo "rm -rf /var/lib/apt/lists/*" waxay yareynayaan cabbirka final image-ka.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Nuqul ka samee requirements.txt si hore loo rakibo dependencies-ka.
# Tani waxay caawisaa in cache-ka la isticmaalo haddii requirements aysan isbeddelin, taasoo dardar gelinaysa build-ka.
COPY requirements.txt .

# Ku rakib Python dependencies-ka.
# "--no-cache-dir" wuxuu yareynayaa cabbirka image-ka.
RUN pip install --no-cache-dir -r requirements.txt

# Nuqul ka samee code-kaaga application-ka ah oo dhan.
# '.' wuxuu matalayaa folder-ka hadda la joogo.
COPY . .

# Muuji dekedda uu app-kaagu ku shaqaynayo.
# Tani waxay muhiim u tahay health check-ka iyo ogaanshaha dekedda ee Koyeb.
EXPOSE 8000

# Qeex command-ka lagu shaqaysiinayo app-kaaga.
# Health check server-ka iyo bot-ka waxay ka bilaabanayaan isla Python script.
CMD ["python", "telegram_tiktok_bot.py"]
