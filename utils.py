"""
utils.py — Core logic for MediaTrace

Handles:
  - Frame extraction from video using OpenCV
  - Perceptual hashing (pHash) via PIL + imagehash
  - Hamming distance comparison for similarity detection
  - YouTube Data API v3 thumbnail fetching
  - Console / email alert when a match is found
  - Gemini AI infringement report generation
"""

import io
import os
import sqlite3
import smtplib
import urllib.request
from datetime import datetime
from email.mime.text import MIMEText

import cv2
import imagehash
import requests
from PIL import Image

# ---------------------------------------------------------------------------
# ★  CONFIG — fill in your YouTube API key below, then save the file
# ---------------------------------------------------------------------------

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "YOUR_YOUTUBE_API_KEY_HERE")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

# One frame extracted per this many seconds (1 = one frame/sec)
FRAME_INTERVAL_SEC = 1

# Hamming distance threshold: 0–64 (lower = stricter)
SIMILARITY_THRESHOLD = 35

# Optional email alerts
ALERT_EMAIL = {
    "enabled":   False,
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "sender":    "you@gmail.com",
    "password":  "your_app_password",
    "recipient": "notify@example.com",
}


# ---------------------------------------------------------------------------
# Frame extraction + hashing
# ---------------------------------------------------------------------------

def extract_and_hash_frames(video_path: str, video_id: str, db_path: str) -> list:
    """
    Opens a video file, grabs one frame every FRAME_INTERVAL_SEC seconds,
    computes a pHash for each, and stores it in SQLite.

    Returns a list of (frame_number, hash_string) tuples.
    Raises RuntimeError if the video cannot be opened.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 25  # safe fallback

    frame_interval = max(1, int(fps * FRAME_INTERVAL_SEC))

    hashes       = []
    frame_index  = 0
    frame_number = 0

    conn = sqlite3.connect(db_path)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_index % frame_interval == 0:
            rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb)
            phash   = str(imagehash.phash(pil_img))
            ts      = frame_index / fps

            conn.execute(
                "INSERT INTO fingerprints (video_id, frame_number, hash_value, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (video_id, frame_number, phash, ts)
            )
            hashes.append((frame_number, phash))
            frame_number += 1

        frame_index += 1

    conn.commit()
    conn.close()
    cap.release()

    print(f"[MediaTrace] Extracted {len(hashes)} frames from '{video_id}'")
    return hashes


# ---------------------------------------------------------------------------
# YouTube thumbnail fetch
# ---------------------------------------------------------------------------

def fetch_youtube_thumbnails(keyword: str, max_results: int = 10) -> list:
    """
    Searches YouTube Data API v3 for videos matching *keyword*.
    Downloads the default thumbnail of each result and computes its pHash.

    Returns a list of dicts:  { 'url': youtube_watch_url, 'thumb_hash': phash_str }
    Returns []  when no API key is configured or the request fails.
    """
    if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "YOUR_YOUTUBE_API_KEY_HERE":
        print("[MediaTrace] WARNING: No YouTube API key set. Returning empty results.")
        return []

    endpoint = "https://www.googleapis.com/youtube/v3/search"
    params   = {
        "part":       "snippet",
        "q":          keyword,
        "type":       "video",
        "maxResults": max_results,
        "key":        YOUTUBE_API_KEY,
    }

    try:
        resp = requests.get(endpoint, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[MediaTrace] YouTube API error: {e}")
        return []

    items = []
    for item in data.get("items", []):
        video_id = item["id"].get("videoId", "")
        if not video_id:
            continue

        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        thumb_url   = item["snippet"]["thumbnails"]["default"]["url"]

        phash = _hash_image_from_url(thumb_url)
        if phash:
            items.append({"url": youtube_url, "thumb_hash": phash})

    print(f"[MediaTrace] Fetched {len(items)} thumbnails for '{keyword}'")
    return items


def _hash_image_from_url(url: str):
    """Download an image from *url* and return its pHash string, or None on failure."""
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            img_data = response.read()
        img = Image.open(io.BytesIO(img_data)).convert("RGB")
        return str(imagehash.phash(img))
    except Exception as e:
        print(f"[MediaTrace] Could not hash image {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Similarity comparison
# ---------------------------------------------------------------------------

def compare_with_database(query_hash_str: str, db_path: str):
    """
    Compares *query_hash_str* against every hash stored in the fingerprints table.

    Returns (similarity_score, video_id)  if best Hamming distance ≤ SIMILARITY_THRESHOLD.
    Returns (None, None)                  if no match found.
    """
    if not query_hash_str:
        return None, None

    query_hash = imagehash.hex_to_hash(query_hash_str)

    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT video_id, hash_value FROM fingerprints").fetchall()
    conn.close()

    if not rows:
        return None, None

    best_distance = float("inf")
    best_video_id = None

    for video_id, stored_hash_str in rows:
        try:
            stored_hash = imagehash.hex_to_hash(stored_hash_str)
            distance    = query_hash - stored_hash
        except Exception:
            continue

        if distance < best_distance:
            best_distance = distance
            best_video_id = video_id

    if best_distance <= SIMILARITY_THRESHOLD:
        similarity_score = 1.0 - (best_distance / 64.0)
        return similarity_score, best_video_id

    return None, None


# ---------------------------------------------------------------------------
# Gemini AI — Infringement Report
# ---------------------------------------------------------------------------

def generate_gemini_report(video_id: str, youtube_url: str, score: float) -> str:
    """
    Calls Google Gemini to generate a short infringement analysis for a detected match.

    Returns a plain-text report string on success, or an empty string if the API
    key is not configured or the call fails. Never raises — the scan must not break.
    """
    if not GEMINI_API_KEY:
        print("[MediaTrace] GEMINI_API_KEY not set — skipping AI report.")
        return ""

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")

        similarity_pct = round(score * 100, 1)
        prompt = (
            f"You are a digital rights analyst for a sports media company. "
            f"MediaTrace, a perceptual fingerprinting system, has detected a potential "
            f"unauthorized re-upload.\n\n"
            f"Original asset ID : {video_id}\n"
            f"Suspect YouTube URL: {youtube_url}\n"
            f"Visual similarity  : {similarity_pct}% (via pHash Hamming distance)\n\n"
            f"Write a concise 2-3 sentence infringement assessment that: "
            f"(1) states the likelihood of unauthorized use based on the similarity score, "
            f"(2) notes what action a rights holder should consider, "
            f"(3) mentions that visual fingerprinting was used — not metadata or watermarks. "
            f"Be professional and factual. Do not use bullet points."
        )

        response = model.generate_content(prompt)
        report = response.text.strip()
        print(f"[MediaTrace] Gemini report generated for {youtube_url}")
        return report

    except Exception as e:
        print(f"[MediaTrace] Gemini report failed (non-fatal): {e}")
        return ""


# ---------------------------------------------------------------------------
# Alert system
# ---------------------------------------------------------------------------

def send_alert(video_id: str, youtube_url: str, score: float):
    """Prints a console alert and optionally sends an email notification."""
    msg = (
        f"\n{'='*60}\n"
        f"  [ALERT] Potential unauthorized usage detected!\n"
        f"  Original video : {video_id}\n"
        f"  YouTube URL    : {youtube_url}\n"
        f"  Similarity     : {score * 100:.1f}%\n"
        f"  Time           : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'='*60}\n"
    )
    print(msg)

    if ALERT_EMAIL.get("enabled"):
        _send_email_alert(video_id, youtube_url, score)


def _send_email_alert(video_id: str, youtube_url: str, score: float):
    """Send a plain-text email via SMTP."""
    cfg     = ALERT_EMAIL
    subject = f"[MediaTrace] Match found for '{video_id}'"
    body    = (
        f"Potential unauthorized usage detected.\n\n"
        f"Original video : {video_id}\n"
        f"YouTube URL    : {youtube_url}\n"
        f"Similarity     : {score * 100:.1f}%\n"
        f"Detected at    : {datetime.now()}\n"
    )
    mime            = MIMEText(body)
    mime["Subject"] = subject
    mime["From"]    = cfg["sender"]
    mime["To"]      = cfg["recipient"]

    try:
        server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])
        server.starttls()
        server.login(cfg["sender"], cfg["password"])
        server.sendmail(cfg["sender"], cfg["recipient"], mime.as_string())
        server.quit()
        print("[MediaTrace] Email alert sent.")
    except Exception as e:
        print(f"[MediaTrace] Email send failed: {e}")