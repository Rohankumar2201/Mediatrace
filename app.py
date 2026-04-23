"""
MediaTrace - Unauthorized Sports Media Detection
Main Flask application entry point
"""

import os
import sqlite3
import tempfile
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from utils import (
    extract_and_hash_frames,
    fetch_youtube_thumbnails,
    compare_with_database,
    send_alert,
    generate_gemini_report,
)

app = Flask(__name__)
app.secret_key = "mediatrace_secret_2024"

# Config
UPLOAD_FOLDER = "/tmp/uploads"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}
DB_PATH = os.path.join(tempfile.gettempdir(), "mediatrace.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def init_db():
    """Create tables if they don't exist yet."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id     TEXT    NOT NULL,
            frame_number INTEGER NOT NULL,
            hash_value   TEXT    NOT NULL,
            timestamp    REAL    NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id         TEXT    NOT NULL,
            youtube_url      TEXT    NOT NULL,
            similarity_score REAL    NOT NULL,
            detected_at      TEXT    NOT NULL,
            gemini_report    TEXT    DEFAULT ''
        )
    """)

    conn.commit()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_all_video_ids():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT DISTINCT video_id FROM fingerprints").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_all_matches():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT video_id, youtube_url, similarity_score, detected_at, gemini_report "
        "FROM matches ORDER BY detected_at DESC"
    ).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    videos  = get_all_video_ids()
    matches = get_all_matches()
    return render_template("index.html", videos=videos, matches=matches)


@app.route("/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        flash("No file part in request.", "error")
        return redirect(url_for("index"))

    file = request.files["video"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Only video files (mp4, avi, mov, mkv) are accepted.", "error")
        return redirect(url_for("index"))

    filename  = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    video_id = os.path.splitext(filename)[0]

    try:
        hashes = extract_and_hash_frames(save_path, video_id, DB_PATH)
        flash(f"Done! Stored {len(hashes)} frame fingerprints for '{video_id}'.", "success")
    except Exception as e:
        flash(f"Error processing video: {e}", "error")

    return redirect(url_for("index"))


@app.route("/scan", methods=["POST"])
def scan_youtube():
    keyword = request.form.get("keyword", "").strip()
    if not keyword:
        flash("Please enter a search keyword.", "error")
        return redirect(url_for("index"))

    results = fetch_youtube_thumbnails(keyword)
    if not results:
        flash("No YouTube results found. Make sure your API key is set.", "warning")
        return redirect(url_for("index"))

    new_matches = 0
    for item in results:
        score, matched_video = compare_with_database(item["thumb_hash"], DB_PATH)
        if matched_video:
            send_alert(matched_video, item["url"], score)

            # ── Gemini AI infringement report ──────────────────────────
            report = generate_gemini_report(matched_video, item["url"], score)
            # ───────────────────────────────────────────────────────────

            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "INSERT INTO matches "
                "(video_id, youtube_url, similarity_score, detected_at, gemini_report) "
                "VALUES (?, ?, ?, datetime('now'), ?)",
                (matched_video, item["url"], round(score, 4), report)
            )
            conn.commit()
            conn.close()
            new_matches += 1

    if new_matches:
        flash(f"Scan complete. {new_matches} potential match(es) found!", "success")
    else:
        flash("Scan complete. No matches found.", "info")

    return redirect(url_for("index"))


@app.route("/api/status")
def api_status():
    videos  = get_all_video_ids()
    matches = get_all_matches()
    return jsonify({
        "indexed_videos": len(videos),
        "total_matches":  len(matches),
        "status": "ok",
        "gemini": "enabled" if os.environ.get("GEMINI_API_KEY") else "not configured",
    })


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    print("MediaTrace running at http://127.0.0.1:5000")
    app.run(debug=True)