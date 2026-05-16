import os
import re
import asyncio
import threading
import tempfile
import logging
import shutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import google.generativeai as genai
from transformers import pipeline

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
# GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "") # Haddeysan la isticmaalayn translation, looma baahna
PORT           = int(os.environ.get("PORT", 8000))

# Initialize Gemini (not needed for transcription in this version, only if you re-enable translation)
# if GEMINI_API_KEY:
#     genai.configure(api_key=GEMINI_API_KEY)
# else:
#     logger.warning("⚠️ DIGNIIN: Gemini API Key lama helin!")

# Initialize Whisper model
logger.info("AI Model-ka Whisper ayaa la isku xirayaa...")
try:
    # Use a smaller model for efficiency if 'base' is too heavy for your server
    # Options: "openai/whisper-tiny", "openai/whisper-small", "openai/whisper-base"
    transcriber = pipeline("automatic-speech-recognition", model="openai/whisper-base")
    logger.info("Whisper model successfully loaded.")
except Exception as e:
    logger.error(f"❌ Cilad ku timid isku xirka Whisper model: {e}")
    transcriber = None # Set to None if it fails to load

# Regex for TikTok URLs
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
    def log_message(self, *a): pass # Suppress HTTP server logging

def start_health_server():
    HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever()

# ══ HELPERS ══

def is_tiktok_url(text):
    m = TIKTOK_RE.search(text)
    if not m: return None
    url = m.group(0)
    return url if url.startswith('http') else 'https://' + url

def download_audio(url):
    """Downloads audio from TikTok URL and returns path to the audio file and its temporary directory."""
    tmpdir = tempfile.mkdtemp()
    output_template = os.path.join(tmpdir, 'audio.%(ext)s')
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '128'}],
        'max_filesize': 50 * 1024 * 1024,  # Max 50MB audio to prevent excessive processing
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find the downloaded file
        for f in os.listdir(tmpdir):
            if f.startswith('audio.') and f.endswith(('.mp3', '.m4a', '.webm', '.ogg', '.wav')):
                return os.path.join(tmpdir, f), tmpdir
        logger.error(f"No audio file found in {tmpdir} after download.")
        return None, tmpdir
    except Exception as e:
        logger.error(f"Audio download error for {url}: {e}")
        return None, tmpdir

def transcribe_with_whisper(audio_path):
    """Transcribes audio using the Hugging Face Whisper pipeline."""
    if not transcriber:
        return "❌ Cilad: Whisper model lama shaqeynayo."
    try:
        logger.info(f"Transcribing audio: {audio_path}")
        # chunk_length_s helps process longer audios by breaking them into chunks
        result = transcriber(audio_path, chunk_length_s=30, generate_kwargs={"task": "transcribe"})
        return result['text'].strip()
    except Exception as e:
        logger.error(f"Whisper transcription error for {audio_path}: {e}")
        return f"❌ Cillad AI-ga dhageysiga ah: {str(e)}"

# Function-ka Gemini translation-ka haddii la rabo in dib loo isticmaalo:
# def translate_with_gemini(english_text):
#     if not GEMINI_API_KEY:
#         return "⚠️ Gemini API Key laguma xirin Settings-ka."
#     if not genai.is_initialized():
#         genai.configure(api_key=GEMINI_API_KEY)
#     
#     try:
#         chosen_model_name = "gemini-1.5-flash" 
#         gemini_model = genai.GenerativeModel(chosen_model_name)
#         
#         prompt = f"""... (your Somali translation prompt) ...\n\n{english_text}"""
#         
#         response = gemini_model.generate_content(prompt)
#         return response.text.strip()
#     except Exception as e:
#         logger.error(f"Gemini translation error: {e}")
#         return f"❌ Cillad dhinaca Gemini ah: {str(e)}"

def get_video_title(url):
    """Gets the title of the video."""
    try:
        with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'TikTok Video')[:70] # Truncate title for display
    except Exception as e:
        logger.warning(f"Could not get video title for {url}: {e}")
        return 'TikTok Video'

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
    user_message = update.message.text or ""
    url = is_tiktok_url(user_message)

    if not url:
        await update.message.reply_text(
            "⚠️ TikTok link ma garanayo.\nTusaale: `https://vm.tiktok.com/xxxxx`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    # Initial loading message
    proc_message = await update.message.reply_text(
        "⏳ *Waan shaqeynayaa...*\n🎬 Video title ayaan helayaa...",
        parse_mode=constants.ParseMode.MARKDOWN
    )
    loop = asyncio.get_event_loop()
    tmpdir = None # Initialize tmpdir outside try block for cleanup

    try:
        # Get video title
        title = await loop.run_in_executor(None, get_video_title, url)
        await proc_message.edit_text(
            f"⏳ *Waan shaqeynayaa...*\n🎬 *{title}*\n"
            "🎤 Codka ayaan soo dejinayaa...",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        logger.info(f"Processing URL: {url} - Title: {title}")

        # Download audio
        audio_path, tmpdir = await loop.run_in_executor(None, download_audio, url)

        if not audio_path:
            await proc_message.edit_text(
                f"❌ *Cilad soo dejinta codka ah*\n\n"
                f"Ma soo dejin karin codka: {title}.\n"
                "Fadlan isku day video kale ama hubi link-ga.",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            return

        await proc_message.edit_text(
            f"⏳ *Waan shaqeynayaa...*\n🎬 *{title}*\n"
            "📝 Codka ayaan qoraal u beddelayaa (Whisper)...",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        logger.info(f"Audio downloaded to: {audio_path}. Starting Whisper transcription.")

        # Transcribe with Whisper (ONLY THIS STEP FOR ENGLISH)
        english_script = await loop.run_in_executor(None, transcribe_with_whisper, audio_path)

        if english_script.startswith("❌"):
            await proc_message.edit_text(
                f"❌ *Cilad qoraal u beddelid ah*\n\n"
                f"Whisper wuu ku guuldareystay: {title}\n"
                f"Sabab: {english_script.replace('❌ Cilad AI-ga dhageysiga ah: ', '')}\n"
                "Fadlan isku day video kale.",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            return
        
        # HADDA LAGUMA BAANNA GEMINI TRANSLATION
        # somali_script = await loop.run_in_executor(None, translate_with_gemini, english_script)

        # Truncate long scripts for Telegram message limits (4096 chars)
        eng_display = english_script[:4000] + ("\n\n...(Qoraalka oo dhan ma soo gelin karo sababtoo ah xaddidaadda Telegram)..." if len(english_script) > 4000 else "")
        # som_display = somali_script[:3500] + ("\n\n...(Qoraalka oo dhan ma soo gelin karo sababtoo ah xaddidaadda Telegram)..." if len(somali_script) > 3500 else "")

        await proc_message.delete() # Delete the loading message

        await update.message.reply_text(
            f"✅ *Script Diyaar!* \n"
            f"🎬 *{title}*\n"
            f"{'─'*28}\n\n"
            f"*🇺🇸 English Script:*\n`{eng_display}`", # Kaliya English ayaan soo bandhigay
            parse_mode=constants.ParseMode.MARKDOWN
        )
        logger.info(f"Successfully processed and sent English script for {url}.")

    except Exception as e:
        logger.error(f"Error in handle_message for {url}: {e}", exc_info=True)
        try:
            await proc_message.edit_text(
                f"❌ *Cilad lama filaan ah dhacday*\n\n`{str(e)[:300]}`\n"
                "Fadlan isku day mar kale ama la xiriir maamulaha.",
                parse_mode=constants.ParseMode.MARKDOWN
            )
        except Exception as edit_e:
            logger.error(f"Failed to edit error message: {edit_e}")
            await update.message.reply_text(
                f"❌ *Cilad lama filaan ah dhacday*\n\n`{str(e)[:300]}`",
                parse_mode=constants.ParseMode.MARKDOWN
            )
    finally:
        # Clean up temporary audio files
        if tmpdir and os.path.exists(tmpdir):
            try:
                shutil.rmtree(tmpdir)
                logger.info(f"Temporary directory cleaned up: {tmpdir}")
            except Exception as e:
                logger.error(f"Failed to delete temporary directory {tmpdir}: {e}")

# ══ MAIN ══

def main():
    if not TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN lama helin. Fadlan ku dar environment variables-ka.")
        raise ValueError("TELEGRAM_TOKEN lama jiro!")
    
    # Start health check server in a separate thread
    threading.Thread(target=start_health_server, daemon=True).start()
    logger.info(f"Health check server started on port {PORT}")

    # Build and run the Telegram bot application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 Telegram Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
