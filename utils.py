"""
utils.py — Core logic for MediaTrace

Handles:
  - Frame extraction from video using OpenCV
  - Perceptual hashing (pHash) via PIL + imagehash
  - Hamming distance comparison for similarity detection
  - YouTube Data API v3 thumbnail fetching
  - Console / email alert when a match is found
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
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Extract one frame every N seconds
FRAME_INTERVAL_SEC = 30

# Maximum number of frames to extract (keeps memory low on free hosting)
MAX_FRAMES = 10

# Hamming distance threshold: 0-64 (lower = stricter)
SIMILARITY_THRESHOLD = 20

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
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 25

    frame_interval = max(1, int(fps * FRAME_INTERVAL_SEC))

    hashes       = []
    frame_index  = 0
    frame_number = 0

    conn = sqlite3.connect(db_path)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_number >= MAX_FRAMES:
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
    if not YOUTUBE_API_KEY:
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
# Alert system
# ---------------------------------------------------------------------------

def send_alert(video_id: str, youtube_url: str, score: float):
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