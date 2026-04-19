# ⬡ MediaTrace

> **Unauthorized sports media detection via perceptual fingerprinting**

MediaTrace extracts perceptual hashes from your original video content, stores them as fingerprints, then continuously compares them against YouTube thumbnails — alerting you the moment your content shows up without permission.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=flat-square&logo=flask&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🧠 How It Works

```
Your Video ──► Extract frames (1/sec) ──► pHash each frame ──► Store in SQLite
                                                                      │
YouTube keyword ──► Fetch thumbnails ──► pHash thumbnail ──► Hamming distance compare
                                                                      │
                                                         Match found? ──► Alert + Log
```

**Perceptual hashing (pHash)** creates a 64-bit fingerprint from an image's visual structure. Two visually similar images will have hashes with a small *Hamming distance* (few bits different). MediaTrace flags anything with distance ≤ 10 (configurable) as a match.

---

## ✨ Features

- 🎥 **Frame-level fingerprinting** — extracts and hashes one frame per second from any video
- 🔍 **YouTube scanning** — searches YouTube Data API v3 and fetches thumbnails automatically
- 📊 **Visual similarity scores** — each match gets a 0–100% similarity score with a progress bar
- 🔔 **Instant alerts** — console alerts on match; optional email notifications via SMTP
- 🗄️ **SQLite storage** — lightweight, zero-config database for fingerprints and matches
- 🖥️ **Clean dashboard** — dark-themed web UI built with Flask + vanilla CSS

---

## 📁 Project Structure

```
MediaTrace/
├── app.py                # Flask routes — upload, scan, dashboard
├── utils.py              # Core logic — pHash, YouTube API, comparison, alerts
├── requirements.txt      # Python dependencies
├── test_local.py         # Offline test — no video or API key needed
├── .env                  # Your secrets (never pushed to Git)
├── .env.example          # Template for collaborators
├── templates/
│   └── index.html        # Dashboard UI (Jinja2 template)
└── static/
    └── style.css         # Dashboard styles
```

---

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/MediaTrace.git
cd MediaTrace
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and add your YouTube Data API v3 key:

```
YOUTUBE_API_KEY=your_actual_key_here
```

**How to get a YouTube API key:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **YouTube Data API v3**
3. Credentials → Create API Key → copy it into `.env`

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

Open your browser at **http://127.0.0.1:5000**

---

## 🎯 Usage

1. **Upload** your original licensed video (mp4 / avi / mov / mkv)
2. **Watch** the terminal — it prints how many frames were fingerprinted
3. **Enter a keyword** in the Scan YouTube box (e.g. `cricket highlights 2024`)
4. **Check Detected Matches** — any unauthorized re-uploads appear with similarity scores and YouTube links

---

## ⚙️ Configuration

All config lives in `utils.py`:

| Setting | Default | Description |
|---|---|---|
| `FRAME_INTERVAL_SEC` | `1` | Extract one frame every N seconds |
| `SIMILARITY_THRESHOLD` | `10` | Max Hamming distance to flag as match (0–64) |
| `ALERT_EMAIL.enabled` | `False` | Set `True` to enable email alerts |

### Tuning the threshold

| Value | Behavior |
|---|---|
| 0–5 | Very strict — near-identical frames only |
| 6–10 | **Default** — similar scenes, handles minor compression/crop |
| 11–20 | Loose — catches more, may produce false positives |

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

> Use a [Gmail App Password](https://myaccount.google.com/apppasswords), not your real Gmail password.

---

## 🧪 API Endpoint

```
GET /api/status
```

Returns a JSON summary of the current database state:

```json
{
  "indexed_videos": 3,
  "total_matches": 7,
  "status": "ok"
}
```

---

## ⚠️ Known Limitations

- Thumbnail-only comparison (not full YouTube video frame extraction)
- No authentication or multi-user support
- SQLite works up to ~100k frames — use PostgreSQL for production scale
- YouTube Data API v3 has a daily quota of 10,000 units (each search = 100 units)

---

## 🛣️ Roadmap

- [ ] Full video frame comparison (not just thumbnails)
- [ ] Batch video upload support
- [ ] PostgreSQL support for production
- [ ] REST API with authentication
- [ ] Scheduled auto-scans
- [ ] Browser extension for one-click reporting

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a pull request.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
