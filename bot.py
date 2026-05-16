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

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── CONFIG ───────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
PORT           = int(os.environ.get("PORT", 8000))  # Koyeb u baahan yahay
# ────────────────────────────────────────────────────────

genai.configure(api_key=GEMINI_API_KEY)

TIKTOK_PATTERN = re.compile(
    r'(https?://)?(www\.)?(vm\.tiktok\.com|tiktok\.com|vt\.tiktok\.com)'
    r'(/[^\s]+)',
    re.IGNORECASE
)

# ════════════════════════════════════════════════════════
#  KOYEB HEALTH CHECK SERVER (Web Service u baahan yahay)
# ════════════════════════════════════════════════════════
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK - TikTok Script Bot Running')

    def log_message(self, format, *args):
        pass  # Health check logs xidh

def start_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"Health server started on port {PORT}")
    server.serve_forever()

# ════════════════════════════════════════════════════════
#  HELPER FUNCTIONS
# ════════════════════════════════════════════════════════

def is_tiktok_url(text: str):
    match = TIKTOK_PATTERN.search(text)
    if match:
        url = match.group(0)
        if not url.startswith('http'):
            url = 'https://' + url
        return url
    return None


def get_tiktok_captions(url: str):
    """Isku day 1: TikTok captions/subtitles ka soo qaad"""
    ydl_opts = {
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en', 'en-US', 'en-GB'],
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subs      = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})
            all_subs  = {**subs, **auto_subs}

            for lang in ['en', 'en-US', 'en-GB', 'en-orig']:
                if lang in all_subs:
                    for fmt in all_subs[lang]:
                        if fmt.get('ext') in ['vtt', 'srv3', 'json3']:
                            import urllib.request
                            with urllib.request.urlopen(fmt['url'], timeout=15) as r:
                                content = r.read().decode('utf-8')
                            text = parse_subtitle(content, fmt.get('ext', ''))
                            if text.strip():
                                return text.strip(), "captions"
    except Exception as e:
        logger.warning(f"Captions failed: {e}")
    return "", ""


def parse_subtitle(content: str, ext: str) -> str:
    import json
    if ext == 'json3':
        try:
            data   = json.loads(content)
            events = data.get('events', [])
            texts  = []
            for event in events:
                segs = event.get('segs', [])
                line = ''.join(s.get('utf8', '') for s in segs).strip()
                if line and line != '\n':
                    texts.append(line)
            return ' '.join(texts)
        except:
            pass

    lines = content.split('\n')
    text_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
            continue
        if re.match(r'\d+:\d+', line):
            continue
        if re.match(r'^\d+$', line):
            continue
        clean = re.sub(r'<[^>]+>', '', line)
        clean = re.sub(r'\{[^}]+\}', '', clean)
        if clean.strip():
            text_lines.append(clean.strip())

    seen, unique = set(), []
    for t in text_lines:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return ' '.join(unique)


def transcribe_with_whisper(url: str):
    """Isku day 2: Audio → Whisper"""
    try:
        import whisper
        model = whisper.load_model("base")

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, 'audio.mp3')
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': audio_path,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'quiet': True,
                'no_warnings': True,
                'max_filesize': 50 * 1024 * 1024,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # File raadi
            found = None
            for f in os.listdir(tmpdir):
                if f.endswith(('.mp3', '.m4a', '.webm', '.ogg')):
                    found = os.path.join(tmpdir, f)
                    break

            if not found:
                return "", ""

            result = model.transcribe(found, language='en')
            text   = result.get('text', '').strip()
            return text, "whisper"

    except Exception as e:
        logger.error(f"Whisper failed: {e}")
        return "", ""


def translate_with_gemini(english_text: str) -> str:
    """Gemini AI → Af Somali"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""Adiga oo ah turjubaan xirfadleh, turjum qoraalkan Af Somali ah.

Xeerarka:
1. Af Somali saafi ah — hadalka dadka caadiga ah
2. Script/TTS-friendly: jumladaha gaagaaban oo cad
3. Ha isticmaalin ereyada adag
4. Macnaha asalka ah xafidh
5. Qoraalka KALIYA soo celi — ha gelineyn sharaxaad

Qoraalka English ah:
{english_text}

Turjumaada Af Somali:"""

        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Gemini failed: {e}")
        return f"❌ Turjumaada waa fashilantay: {str(e)}"


def get_video_title(url: str) -> str:
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('title', 'TikTok Video')[:100]
    except:
        return 'TikTok Video'


# ════════════════════════════════════════════════════════
#  TELEGRAM HANDLERS
# ════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Salaan! Waxaan ahay TikTok Script Bot*\n\n"
        "📌 *Sida loo isticmaalo:*\n"
        "1️⃣ TikTok link i soo dir\n"
        "2️⃣ Script English ah ayaan soo saari\n"
        "3️⃣ Af Somali ayaan ku turjumi\n\n"
        "✅ *Tusaale:*\n"
        "`https://www.tiktok.com/@user/video/123456`\n\n"
        "🚀 Bilow hadda!",
        parse_mode=constants.ParseMode.MARKDOWN
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ *Caawimad*\n\n"
        "• /start — Bot bilow\n"
        "• /help — Caawimad\n\n"
        "🔗 TikTok link dir, bot-ku wuxuu:\n"
        "1. Captions/subtitles ka soo qaadaa\n"
        "2. Haddaan jirin → Whisper AI transcribe\n"
        "3. Gemini AI → Af Somali turjumaa",
        parse_mode=constants.ParseMode.MARKDOWN
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    url  = is_tiktok_url(text)

    if not url:
        await update.message.reply_text(
            "⚠️ TikTok link ma garanayo.\n\n"
            "Fadlan link-ka sax ah dir:\n"
            "`https://www.tiktok.com/@user/video/123456`",
            parse_mode=constants.ParseMode.MARKDOWN
        )
        return

    proc = await update.message.reply_text(
        "⏳ *Waan shaqeynayaa...*\n📥 Captions raadineynaa...",
        parse_mode=constants.ParseMode.MARKDOWN
    )

    try:
        # Title
        title = await asyncio.get_event_loop().run_in_executor(None, get_video_title, url)

        await proc.edit_text(
            f"⏳ *Waan shaqeynayaa...*\n🎬 *{title[:60]}*\n📥 Captions raadineynaa...",
            parse_mode=constants.ParseMode.MARKDOWN
        )

        # Step 1: Captions
        english_text, method = await asyncio.get_event_loop().run_in_executor(
            None, get_tiktok_captions, url
        )

        # Step 2: Whisper haddaan captions jirin
        if not english_text:
            await proc.edit_text(
                f"⏳ *Waan shaqeynayaa...*\n🎬 *{title[:60]}*\n"
                f"⚠️ Captions lama helin\n🎤 Whisper AI transcribing...",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            english_text, method = await asyncio.get_event_loop().run_in_executor(
                None, transcribe_with_whisper, url
            )

        if not english_text:
            await proc.edit_text(
                "❌ *Script-ka lama helin*\n\n"
                "• Video private yahay?\n"
                "• Captions la'aan?\n"
                "• Link-ka hubi",
                parse_mode=constants.ParseMode.MARKDOWN
            )
            return

        # Step 3: Translate
        await proc.edit_text(
            f"⏳ *Waan shaqeynayaa...*\n🎬 *{title[:60]}*\n"
            f"✅ Script helay ({method})\n🌍 Af Somali turjumeynaa...",
            parse_mode=constants.ParseMode.MARKDOWN
        )

        somali_text = await asyncio.get_event_loop().run_in_executor(
            None, translate_with_gemini, english_text
        )

        # Natiijada
        method_icon  = "📝" if method == "captions" else "🎤"
        method_label = "Captions" if method == "captions" else "Whisper AI"

        eng_chunk = english_text[:3500] + ("..." if len(english_text) > 3500 else "")
        som_chunk = somali_text[:3500]   + ("..." if len(somali_text)  > 3500 else "")

        await proc.delete()

        # Part 1 — English
        await update.message.reply_text(
            f"✅ *Script Diyaar!*\n"
            f"{method_icon} Ilo: *{method_label}*\n"
            f"🎬 *{title[:80]}*\n"
            f"{'─'*28}\n\n"
            f"🇺🇸 *Script English:*\n{eng_chunk}",
            parse_mode=constants.ParseMode.MARKDOWN
        )

        await asyncio.sleep(0.4)

        # Part 2 — Somali
        await update.message.reply_text(
            f"🇸🇴 *Turjumaada Af Somali:*\n{'─'*28}\n\n{som_chunk}",
            parse_mode=constants.ParseMode.MARKDOWN
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        await proc.edit_text(
            f"❌ *Cilad dhacday*\n\n`{str(e)[:300]}`",
            parse_mode=constants.ParseMode.MARKDOWN
        )


# ════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════

def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN environment variable ma jiro!")
    if not GEMINI_API_KEY:
        raise ValueError("❌ GEMINI_API_KEY environment variable ma jiro!")

    # Health check server thread-ka ku bilow (Koyeb port u baahan yahay)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    logger.info(f"✅ Health server running on port {PORT}")

    # Telegram bot bilow
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help",  help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🤖 TikTok Script Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
