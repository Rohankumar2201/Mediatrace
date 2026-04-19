"""
utils.py — Core logic for MediaTrace

Handles:
  - Frame extraction from video using OpenCV
  - Perceptual hashing (pHash) via PIL + imagehash
  - Hamming distance comparison for similarity detection
  - YouTube Data API v3 thumbnail + storyboard fetching
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

FRAME_INTERVAL_SEC = 30
MAX_FRAMES = 10
SIMILARITY_THRESHOLD = 35

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
    Opens a video, seeks to 10 evenly spaced timestamps,
    hashes each frame and stores in SQLite.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    duration_sec = total_frames / fps

    num_samples = min(MAX_FRAMES, max(1, int(duration_sec // FRAME_INTERVAL_SEC)))
    timestamps = [duration_sec * i / num_samples for i in range(num_samples)]

    hashes = []
    conn = sqlite3.connect(db_path)

    for i, ts in enumerate(timestamps):
        cap.set(cv2.CAP_PROP_POS_MSEC, ts * 1000)
        ret, frame = cap.read()
        if not ret:
            continue
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        phash = str(imagehash.phash(pil_img))
        conn.execute(
            "INSERT INTO fingerprints (video_id, frame_number, hash_value, timestamp) VALUES (?, ?, ?, ?)",
            (video_id, i, phash, ts)
        )
        hashes.append((i, phash))

    conn.commit()
    conn.close()
    cap.release()

    print(f"[MediaTrace] Extracted {len(hashes)} frames from '{video_id}'")
    return hashes


# ---------------------------------------------------------------------------
# YouTube storyboard frame extraction
# ---------------------------------------------------------------------------

def _get_storyboard_hashes(video_id: str) -> list:
    """
    Downloads YouTube's storyboard sprite sheet for a video.
    These are REAL video frames used for the scrubber preview.
    Splits the sprite sheet into individual tiles and hashes each one.
    Returns a list of pHash strings.
    """
    # YouTube storyboard URLs — L2 has larger tiles (160x90), L1 has smaller (120x68)
    storyboard_urls = [
        f"https://i.ytimg.com/sb/{video_id}/storyboard3_L2/M0.jpg",
        f"https://i.ytimg.com/sb/{video_id}/storyboard3_L1/M0.jpg",
    ]

    for url in storyboard_urls:
        try:
            with urllib.request.urlopen(url, timeout=8) as response:
                img_data = response.read()

            sprite = Image.open(io.BytesIO(img_data)).convert("RGB")
            w, h = sprite.size

            # Tile dimensions per storyboard level
            tile_w = 160 if "L2" in url else 120
            tile_h = 90  if "L2" in url else 68

            cols = w // tile_w
            rows = h // tile_h

            hashes = []
            for row in range(rows):
                for col in range(cols):
                    left = col * tile_w
                    top  = row * tile_h
                    tile = sprite.crop((left, top, left + tile_w, top + tile_h))
                    if tile.size[0] > 10 and tile.size[1] > 10:
                        hashes.append(str(imagehash.phash(tile)))

            if hashes:
                print(f"[MediaTrace] Got {len(hashes)} storyboard frames for {video_id}")
                return hashes

        except Exception as e:
            print(f"[MediaTrace] Storyboard fetch failed {url}: {e}")
            continue

    return []


# ---------------------------------------------------------------------------
# YouTube thumbnail fetch
# ---------------------------------------------------------------------------

def fetch_youtube_thumbnails(keyword: str, max_results: int = 10) -> list:
    """
    Searches YouTube Data API v3 for videos matching keyword.
    For each result, fetches BOTH storyboard frames (real video frames)
    AND all thumbnail sizes, hashes each, and returns them all for comparison.
    """
    if not YOUTUBE_API_KEY:
        print("[MediaTrace] WARNING: No YouTube API key set.")
        return []

    endpoint = "https://www.googleapis.com/youtube/v3/search"
    params = {
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
        vid_id = item["id"].get("videoId", "")
        if not vid_id:
            continue

        youtube_url = f"https://www.youtube.com/watch?v={vid_id}"

        # 1. Try storyboard frames first — real video frames, best for matching
        storyboard_hashes = _get_storyboard_hashes(vid_id)
        for h in storyboard_hashes:
            items.append({"url": youtube_url, "thumb_hash": h})

        # 2. Also try all thumbnail sizes as fallback
        thumbnails = item["snippet"]["thumbnails"]
        for quality in ["maxres", "high", "medium", "default"]:
            thumb_url = thumbnails.get(quality, {}).get("url")
            if not thumb_url:
                continue
            phash = _hash_image_from_url(thumb_url)
            if phash:
                items.append({"url": youtube_url, "thumb_hash": phash})
                break  # one thumbnail per video is enough

    print(f"[MediaTrace] Total hashes to compare for '{keyword}': {len(items)}")
    return items


def _hash_image_from_url(url: str):
    """Download an image from url and return its pHash string, or None on failure."""
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
    Compares query_hash_str against every stored fingerprint.
    Returns (similarity_score, video_id) if match found, else (None, None).
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
            distance = query_hash - stored_hash
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
    cfg = ALERT_EMAIL
    subject = f"[MediaTrace] Match found for '{video_id}'"
    body = (
        f"Potential unauthorized usage detected.\n\n"
        f"Original video : {video_id}\n"
        f"YouTube URL    : {youtube_url}\n"
        f"Similarity     : {score * 100:.1f}%\n"
        f"Detected at    : {datetime.now()}\n"
    )
    mime = MIMEText(body)
    mime["Subject"] = subject
    mime["From"] = cfg["sender"]
    mime["To"] = cfg["recipient"]

    try:
        server = smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"])
        server.starttls()
        server.login(cfg["sender"], cfg["password"])
        server.sendmail(cfg["sender"], cfg["recipient"], mime.as_string())
        server.quit()
        print("[MediaTrace] Email alert sent.")
    except Exception as e:
        print(f"[MediaTrace] Email send failed: {e}")