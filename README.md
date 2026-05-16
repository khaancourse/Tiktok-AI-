# 🤖 TikTok Script Bot — Koyeb Deployment

---

## 📋 Files-ka

```
tiktok-bot/
├── bot.py           ← Main bot (health server ku jira)
├── requirements.txt ← Python packages
├── Dockerfile       ← Koyeb Docker image
└── README.md        ← Tilmaamahan
```

---

## 🚀 Tallaabada Koyeb

### Tallaabo 1: Telegram Token hel
1. Telegram: **@BotFather** → `/newbot`
2. Magac: `KhaanFilms Script Bot`
3. Username: `khaanfilms_script_bot` (ama mid kale)
4. **Token-ka** koobiyee ✅

---

### Tallaabo 2: Gemini API Key hel
1. Fur: **https://aistudio.google.com/app/apikey**
2. Guji **"Create API Key"**
3. **Key-ga** koobiyee ✅

---

### Tallaabo 3: GitHub Repo samee
1. **https://github.com** → New repository
2. Magac: `tiktok-script-bot` (Public)
3. Files 4-ta upload:
   - `bot.py`
   - `requirements.txt`
   - `Dockerfile`

---

### Tallaabo 4: Koyeb Deploy

1. **https://app.koyeb.com** → **"Create Service"**
2. **"Web Service"** dooro
3. **"GitHub"** dooro
4. Repo-gaaga dooro: `tiktok-script-bot`

**Settings:**
| Field | Value |
|-------|-------|
| Service name | `tiktok-script-bot` |
| Builder | `Dockerfile` |
| Port | `8000` |
| Instance | `Free` |

5. **"Environment variables"** section:

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | *token-kaaga* |
| `GEMINI_API_KEY` | *api key-gaaga* |

6. Guji **"Deploy"** ✅

---

## ✅ Test

```
Telegram → @your_bot → /start
Markaas link dir:
https://vm.tiktok.com/xxxxx
```

---

## ⚙️ Sida u shaqeyso

```
TikTok Link
    ↓
1. Captions (yt-dlp)
    ↓ haddaan jirin
2. Audio → Whisper AI
    ↓
3. Gemini → Af Somali
    ↓
Script English + Somali ✅
```

---

## 🔧 Koyeb Free Tier

- ✅ **$5.75/bilood credit** bilaash
- ✅ Always-on (spin down ma laha)
- ✅ Docker support
- ⚠️ RAM: 512MB (Whisper base model wuu shaqeeyaa)
