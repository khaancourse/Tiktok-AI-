import os
import re
import asyncio
import threading
import tempfile
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import google.generativeai as genai

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PORT           = int(os.environ.get("PORT", 8000))

genai.configure(api_key=GEMINI_API_KEY)

TIKTOK_RE = re.compile(
    r'(https?://)?(www\.)?(vm\.tiktok\.com|tiktok\.com|vt\.tiktok\.com)(/[^\s]+)',
    re.IGNORECASE
)

# ══ HEALTH CHECK (Koyeb port u baahan yahay) ══
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')
    def log_message(self, *a): pass

def start_health_server():
    HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever()

# ══ HELPERS ══

def is_tiktok(text):
    m = TIKTOK_RE.search(text)
    if not m: return None
    url = m.group(0)
    return url if url.startswith('http') else 'https://' + url

def get_captions(url):
    """TikTok captions/subtitles ka soo qaad"""
    try:
        with yt_dlp.YoutubeDL({'writesubtitles':True,'writeautomaticsub':True,
                                'subtitleslangs':['en','en-US'],'skip_download':True,
                                'quiet':True,'no_warnings':True}) as ydl:
            info = ydl.extract_info(url, download=False)
            all_subs = {**info.get('subtitles',{}), **info.get('automatic_captions',{})}
            for lang in ['en','en-US','en-GB']:
                if lang in all_subs:
                    for fmt in all_subs[lang]:
                        if fmt.get('ext') in ['vtt','json3','srv3']:
                            import urllib.request
                            with urllib.request.urlopen(fmt['url'], timeout=15) as r:
                                content = r.read().decode('utf-8')
                            text = clean_subtitle(content, fmt.get('ext',''))
                            if text.strip():
                                return text.strip()
    except Exception as e:
        logger.warning(f"Captions error: {e}")
    return ""

def clean_subtitle(content, ext):
    import json
    if ext == 'json3':
        try:
            data = json.loads(content)
            parts = []
            for ev in data.get('events',[]):
                line = ''.join(s.get('utf8','') for s in ev.get('segs',[])).strip()
                if line and line != '\n': parts.append(line)
            return ' '.join(parts)
        except: pass
    lines, seen, out = content.split('\n'), set(), []
    for l in lines:
        l = l.strip()
        if not l or l.startswith('WEBVTT') or re.match(r'\d+:\d+',l) or re.match(r'^\d+$',l): continue
        clean = re.sub(r'<[^>]+>','',l).strip()
        if clean and clean not in seen:
            seen.add(clean); out.append(clean)
    return ' '.join(out)

def download_audio(url):
    """Audio ka soo qaad (Gemini transcription u baahan)"""
    try:
        tmpdir = tempfile.mkdtemp()
        out = os.path.join(tmpdir, 'audio.mp3')
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': out,
            'postprocessors': [{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'64'}],
            'quiet': True, 'no_warnings': True,
            'max_filesize': 20 * 1024 * 1024,  # 20MB max
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        # File raadi
        for f in os.listdir(tmpdir):
            if f.endswith(('.mp3','.m4a','.webm','.ogg')):
                return os.path.join(tmpdir, f), tmpdir
    except Exception as e:
        logger.error(f"Audio download error: {e}")
    return None, None

def gemini_transcribe(audio_path):
    """Gemini 1.5 Flash audio transcribe"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        with open(audio_path, 'rb') as f:
            audio_data = f.read()
        
        import base64
        audio_b64 = base64.b64encode(audio_data).decode()
        
        response = model.generate_content([
            {
                "inline_data": {
                    "mime_type": "audio/mp3",
                    "data": audio_b64
                }
            },
            "Transcribe this audio exactly as spoken in English. Return only the transcript text, no timestamps or labels."
        ])
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini transcribe error: {e}")
        return ""

def gemini_translate(english_text):
    """Gemini → Af Somali turjum"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(
            f"""Turjum qoraalkan Af Somali ah. Xeerarka:
1. Af Somali saafi ah — hadalka caadiga ah
2. TTS-friendly: jumladaha gaagaaban
3. Macnaha asalka ah xafidh
4. Qoraalka KALIYA soo celi

English:
{english_text}

Af Somali:"""
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini translate error: {e}")
        return f"❌ Turjumaada waa fashilantay: {e}"

def get_title(url):
    try:
        with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True}) as ydl:
            return ydl.extract_info(url, download=False).get('title','TikTok Video')[:80]
    except: return 'TikTok Video'

# ══ TELEGRAM HANDLERS ══

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Salaan! Waxaan ahay TikTok Script Bot*\n\n"
        "📌 *Sida loo isticmaalo:*\n"
        "1️⃣ TikTok link i soo dir\n"
        "2️⃣ Script English ah ayaan soo saari\n\n"
        "✅ *Tusaale:*\n`https://vm.tiktok.com/xxxxx`",
        parse_mode=constants.ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = is_tiktok(update.message.text or "")
    if not url:
        await update.message.reply_text(
            "⚠️ TikTok link ma garanayo.\nTusaale: `https://vm.tiktok.com/xxxxx`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    proc = await update.message.reply_text(
        "⏳ *Waan shaqeynayaa...*\n📥 Captions raadineynaa...",
        parse_mode=constants.ParseMode.MARKDOWN
    )
    loop = asyncio.get_event_loop()

    try:
        title = await loop.run_in_executor(None, get_title, url)
        await proc.edit_text(
            f"⏳ *Waan shaqeynayaa...*\n🎬 *{title[:55]}*\n📥 Captions raadineynaa...",
            parse_mode=constants.ParseMode.MARKDOWN
        )

        # Step 1: Captions
        english = await loop.run_in_executor(None, get_captions, url)
        method  = "📝 Captions"

        # Step 2: Haddaan captions jirin → Audio download + Gemini transcribe
        if not english:
            await proc.edit_text(
                f"⏳ *Waan shaqeynayaa...*\n🎬 *{title[:55]}*\n"
                f"⚠️ Captions lama helin\n🎤 Audio ka soo rarinayaa...",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            audio_path, tmpdir = await loop.run_in_executor(None, download_audio, url)

            if audio_path and os.path.exists(audio_path):
                await proc.edit_text(
                    f"⏳ *Waan shaqeynayaa...*\n🎬 *{title[:55]}*\n"
                    f"🎤 Gemini audio transcribing...",
                    parse_mode=constants.ParseMode.MARKDOWN
                )
                english = await loop.run_in_executor(None, gemini_transcribe, audio_path)
                method  = "🎤 Gemini Audio"
                try:
                    import shutil; shutil.rmtree(tmpdir, ignore_errors=True)
                except: pass

        if not english:
            await proc.edit_text(
                "❌ *Script-ka lama helin*\n\n"
                "Sababaha:\n"
                "• Video captions/subtitles kuma jiraan\n"
                "• Audio-ga Gemini kama heli karin\n"
                "• Filimka af kale ku hadlayaa (English ma aha)\n\n"
                "Isku day video kale.",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            return

        await proc.delete()

        # English script kaliya soo dir
        eng = english[:4000] + ("..." if len(english) > 4000 else "")

        await update.message.reply_text(
            f"✅ *Script Diyaar!* {method}\n"
            f"🎬 *{title[:70]}*\n"
            f"{'─'*28}\n\n"
            f"{eng}",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            await proc.edit_text(
                f"❌ *Cilad dhacday*\n\n`{str(e)[:300]}`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        except: pass

# ══ MAIN ══

def main():
    if not TELEGRAM_TOKEN: raise ValueError("TELEGRAM_TOKEN ma jiro!")
    if not GEMINI_API_KEY:  raise ValueError("GEMINI_API_KEY ma jiro!")

    threading.Thread(target=start_health_server, daemon=True).start()
    logger.info(f"Health server: port {PORT}")

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
