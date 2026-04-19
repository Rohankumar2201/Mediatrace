<div align="center">

# ⬡ MediaTrace

### Unauthorized Sports Media Detection via Perceptual Fingerprinting

*Upload your original video. Scan YouTube. Find unauthorized re-uploads instantly.*

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![YouTube API](https://img.shields.io/badge/YouTube-Data%20API%20v3-FF0000?style=flat-square&logo=youtube&logoColor=white)](https://developers.google.com/youtube/v3)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-mediatrace.onrender.com-f5a623?style=flat-square)](https://mediatrace.onrender.com)

---

**🌐 Live Demo → [https://mediatrace.onrender.com](https://mediatrace.onrender.com)**

</div>

---

## 🧠 What is MediaTrace?

MediaTrace is a content protection tool built for sports media rights holders. It automatically detects when your licensed video content is being re-uploaded to YouTube without authorization — using perceptual hashing and visual fingerprinting, not metadata or watermarks.

No watermark needed. No manual searching. Just upload your video, enter a keyword, and MediaTrace does the rest.

---

## 🎯 How It Works

```
Your Video
    │
    ▼
Extract Frames          ← OpenCV seeks to evenly spaced timestamps
    │
    ▼
pHash Each Frame        ← 64-bit perceptual fingerprint per frame
    │
    ▼
Store in SQLite         ← Fingerprint database built locally
    │
    ▼
Search YouTube          ← YouTube Data API v3 keyword search
    │
    ▼
Fetch Storyboard        ← Real video frames from YouTube's scrubber preview
+ Thumbnails            ← All available thumbnail resolutions
    │
    ▼
Hamming Distance        ← Compare every YouTube frame against your fingerprints
    │
    ▼
Match Found?            ← Flag + log + alert
```

**Perceptual hashing (pHash)** creates a 64-bit fingerprint from the visual structure of an image. Two visually similar images produce hashes with a small *Hamming distance* — few bits different. MediaTrace flags anything within the configured threshold as a potential unauthorized re-upload.

**Storyboard comparison** is the key innovation — instead of just comparing against YouTube thumbnails (which are custom graphics), MediaTrace downloads YouTube's internal scrubber preview sprite sheets, which contain *real video frames*. This gives dramatically more accurate matching.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎥 **Smart Frame Extraction** | Seeks directly to evenly spaced timestamps — no sequential scanning, fast even on large files |
| 🔍 **YouTube Storyboard Analysis** | Compares against real YouTube video frames, not just thumbnails |
| 📊 **Visual Similarity Scores** | Every match gets a 0–100% similarity score with an animated progress bar |
| 🔔 **Instant Alerts** | Console alerts on match detection; optional SMTP email notifications |
| 🗄️ **SQLite Fingerprint DB** | Lightweight, zero-config database for storing and querying fingerprints |
| 🖥️ **Dark Dashboard UI** | Clean, professional dark-themed web interface built with Flask |
| ⚡ **REST API** | `/api/status` endpoint for integration and monitoring |

---

## 🚀 Live Demo

**URL:** [https://mediatrace.onrender.com](https://mediatrace.onrender.com)

### Try it yourself:

1. Download any short sports clip (or use your own)
2. Go to the live URL
3. Upload the video under **Step 01**
4. Enter `Cricket World Cup 2011 Final India Sri Lanka ICC` under **Step 02**
5. Hit **Run Scan**
6. Watch matches appear in the **Detected Matches** panel with similarity scores and YouTube links

> ⚠️ First load may take ~30 seconds if the server was idle (free tier spin-down). This is normal.

---

## 📁 Project Structure

```
MediaTrace/
├── app.py                  # Flask routes — upload, scan, dashboard, API
├── utils.py                # Core logic — pHash, storyboard fetch, comparison, alerts
├── requirements.txt        # Python dependencies
├── test_local.py           # Offline test — no video or API key needed
├── render.yaml             # Render deployment config
├── .env                    # Your secrets (never pushed to Git)
├── .env.example            # Template for collaborators
├── .gitignore              # Protects secrets and build artifacts
├── templates/
│   └── index.html          # Dashboard UI (Jinja2 template)
└── static/
    └── style.css           # Dashboard styles
```

---

## ⚡ Quick Start (Local)

### 1. Clone the repository

```bash
git clone https://github.com/Rohankumar2201/Mediatrace.git
cd Mediatrace
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up your YouTube API key

```bash
cp .env.example .env
```

Open `.env` and add your key:
```
YOUTUBE_API_KEY=your_actual_key_here
```

**How to get a YouTube API key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **YouTube Data API v3**
3. Credentials → Create API Key → paste it in `.env`

### 4. Run the offline test

```bash
python test_local.py
```

Expected output:
```
✓ MATCH DETECTED — pipeline working correctly!
Correctly rejected ✓
```

### 5. Start the app

```bash
python app.py
```

Open **http://127.0.0.1:5000**

---

## 🎯 Usage

| Step | Action | What Happens |
|---|---|---|
| **01** | Upload your licensed video | OpenCV extracts frames, pHash fingerprints stored in SQLite |
| **02** | Enter a YouTube keyword | YouTube API searched, storyboard frames + thumbnails fetched and hashed |
| **03** | View Indexed Videos | All uploaded videos listed |
| **04** | Check Detected Matches | Unauthorized re-uploads shown with similarity scores and YouTube links |

---

## ⚙️ Configuration

All config lives in `utils.py`:

| Setting | Default | Description |
|---|---|---|
| `FRAME_INTERVAL_SEC` | `30` | Seconds between extracted frames |
| `MAX_FRAMES` | `10` | Maximum frames extracted per video |
| `SIMILARITY_THRESHOLD` | `35` | Max Hamming distance to flag as match (0–64) |

### Threshold guide

| Value | Behavior |
|---|---|
| 0–10 | Very strict — near-identical only |
| 11–20 | Moderate — handles slight compression |
| 21–35 | **Default** — handles resizing, re-encoding, format changes |
| 36–50 | Loose — catches heavily modified content, more false positives |

---

## 📧 Email Alerts

In `utils.py`, update the `ALERT_EMAIL` block:

```python
ALERT_EMAIL = {
    "enabled":   True,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "sender":    "you@gmail.com",
    "password":  "your_gmail_app_password",
    "recipient": "notify@example.com",
}
```

> Use a [Gmail App Password](https://myaccount.google.com/apppasswords), not your real password.

---

## 🔌 API

```
GET /api/status
```

```json
{
  "indexed_videos": 2,
  "total_matches": 10,
  "status": "ok"
}
```

---

## 🛣️ Roadmap

- [x] Frame-level perceptual fingerprinting
- [x] YouTube storyboard frame comparison
- [x] Visual similarity scoring dashboard
- [x] Live deployment
- [ ] Full YouTube video frame extraction (not just storyboards)
- [ ] Batch video upload support
- [ ] Scheduled auto-scans with cron
- [ ] PostgreSQL support for production scale
- [ ] REST API with authentication
- [ ] Browser extension for one-click reporting
- [ ] DMCA takedown request automation

---

## ⚠️ Known Limitations

- Storyboard tiles are small (160×90px) — very heavy compression can push Hamming distance above threshold
- SQLite resets on Render redeploy — use PostgreSQL for persistent production storage
- YouTube API daily quota: 10,000 units (each search = 100 units)
- Free Render tier: 512MB RAM — works for short/medium videos

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ for Google Hackathon 2024

**[Live Demo](https://mediatrace.onrender.com)** · **[Report Bug](../../issues)** · **[Request Feature](../../issues)**

</div>