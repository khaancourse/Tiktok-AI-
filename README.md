# 🎙️ TikTok Script & Somali AI Telegram Bot

Bot-kan Telegram wuxuu u turjumaa fiidiyowyada TikTok qoraal (script) English ah oo uu isticmaalayo model-ka **Whisper** ee Hugging Face, ka dibna wuxuu qoraalkaas u turjumaa Af-Soomaali dabiici ah oo TTS (Text-to-Speech) friendly ah isagoo isticmaalaya **Google Gemini**.

## 🌟 Tilmaamaha Muhiimka ah

*   **Soo Dejinta Fiiyowga TikTok:** Wuxuu isticmaalaa `yt-dlp` si uu u soo dejiyo qaybta codka ee fiidiyowga TikTok.
*   **Qoraal u Beddelid English ah:** Wuxuu isticmaalaa model-ka Whisper (openai/whisper-base) si uu codka ugu beddelo qoraal (transcription) English ah.
*   **Turjumid Af-Soomaali ah oo Dabiici ah:** Wuxuu isticmaalaa Google Gemini si uu qoraalka English-ka ah ugu turjumo Af-Soomaali. Gemini wuxuu adeegsadaa prompt gaar ah si uu turjumaadda uga dhigo mid u eeg sheeko bini-aadam ah, oo nambarada iyo boqolleyda u qoraa qaab afka lagu dhawaaqo, taasoo ka dhigaysa mid ku habboon TTS.
*   **Feedback Dhameystiran:** Wuxuu siiyaa isticmaalaha fariimo macno leh inta uu shaqeynayo (soo dejin, transcribe-gareyn, turjumid) iyo haddii ay cilad dhacdo.
*   **Diyaar u ah Deployment:** Wuxuu ku habboon yahay in lagu geeyo adeegyada Cloud-ka sida Koyeb, isagoo adeegsanaya `Dockerfile` iyo health check.

## 🚀 Sida Loo Isticmaalo Bot-ka

1.  **Bilow Bot-ka:** Ka bilow bot-ka Telegram adigoo riixaya `/start`.
2.  **Geli Link-ga TikTok:** U soo dir bot-ka link-ga fiidiyowga TikTok (tusaale: `https://vm.tiktok.com/xxxxx`).
3.  **Sug:** Bot-ku wuxuu marka hore soo dejisan doonaa codka, ka dibna wuxuu u beddeli doonaa qoraal English ah oo uu isticmaalayo Whisper, ugu dambayntiina wuxuu u turjumi doonaa Af-Soomaali isagoo isticmaalaya Gemini.
4.  **Hel Script-ka:** Waxaad heli doontaa script-ka English-ka ah iyo turjumaadda Af-Soomaaliga ah ee fiidiyowgaaga.

## ⚙️ Sida Loo Geeyo (Deployment)

Bot-kan waxaa loogu talagalay in lagu geeyo deegaanada Cloud-ka sida Koyeb.

### 1. Shuruudaha

*   **Telegram Bot Token:** Waxaad ka heli kartaa `@BotFather` ee Telegram.
*   **Google Gemini API Key:** Abuur key ka Google AI Studio: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).
*   **Git Repository:** Code-kaaga waa inuu ku jiraa repository Git ah (GitHub, GitLab, iwm.).

### 2. Dejinta Faylasha Mashruuca

Hubi in faylasha soo socda ay ku jiraan xididka (root) repositooriyadaada Git:

*   `telegram_tiktok_bot.py` (Main bot code)
*   `requirements.txt` (Python dependencies)
*   `Dockerfile` (Docker build instructions)
*   `README.md` (Faylkan)

### 3. `requirements.txt`
