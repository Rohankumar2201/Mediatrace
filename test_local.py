"""
test_local.py — Offline sanity check for MediaTrace

Simulates the fingerprinting pipeline without needing
a real video or a YouTube API key.

Run with:  python test_local.py
"""

import os
import sqlite3
import numpy as np
from PIL import Image
import imagehash

DB_PATH = "test_mediatrace.db"


def setup_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fingerprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            frame_number INTEGER,
            hash_value TEXT,
            timestamp REAL
        )
    """)
    conn.commit()
    return conn


def fake_frame(seed: int, noise: int = 0) -> Image.Image:
    """Generate a reproducible fake image frame. Add noise to simulate variation."""
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 256, (240, 320, 3), dtype=np.uint8)
    if noise > 0:
        perturbation = np.random.randint(-noise, noise, base.shape, dtype=np.int16)
        base = np.clip(base.astype(np.int16) + perturbation, 0, 255).astype(np.uint8)
    return Image.fromarray(base, "RGB")


def test_store_and_match():
    print("=" * 55)
    print("  MediaTrace — Local Fingerprint Test")
    print("=" * 55)

    conn = setup_db()

    # Step 1: Store 5 fake frames as the "original" video
    print("\n[1] Storing fingerprints for 'original_match_video'...")
    original_hashes = []
    for i in range(5):
        img = fake_frame(seed=42 + i)          # deterministic frames
        h = str(imagehash.phash(img))
        conn.execute(
            "INSERT INTO fingerprints (video_id, frame_number, hash_value, timestamp) VALUES (?, ?, ?, ?)",
            ("original_match_video", i, h, float(i))
        )
        original_hashes.append(h)
        print(f"   Frame {i}: {h}")
    conn.commit()

    # Step 2: Simulate a "YouTube thumbnail" that is nearly identical (slight noise)
    print("\n[2] Simulating a near-duplicate YouTube thumbnail...")
    suspect_img = fake_frame(seed=42, noise=5)   # same seed, tiny noise
    suspect_hash = str(imagehash.phash(suspect_img))
    print(f"   Suspect hash: {suspect_hash}")

    # Step 3: Compare with stored hashes
    print("\n[3] Comparing suspect hash against database...")
    rows = conn.execute("SELECT video_id, hash_value FROM fingerprints").fetchall()
    conn.close()

    best_dist = float("inf")
    best_vid = None
    for vid, stored_h in rows:
        dist = imagehash.hex_to_hash(suspect_hash) - imagehash.hex_to_hash(stored_h)
        if dist < best_dist:
            best_dist = dist
            best_vid = vid

    THRESHOLD = 10
    similarity = 1.0 - (best_dist / 64.0)
    print(f"   Best match    : {best_vid}")
    print(f"   Hamming dist  : {best_dist}  (threshold = {THRESHOLD})")
    print(f"   Similarity    : {similarity * 100:.1f}%")

    if best_dist <= THRESHOLD:
        print("\n   ✓ MATCH DETECTED — pipeline working correctly!")
    else:
        print("\n   ✗ No match found (might need to tune threshold).")

    # Step 4: Verify a truly unrelated hash does NOT match
    print("\n[4] Testing an unrelated image (should NOT match)...")
    unrelated_img = fake_frame(seed=999, noise=0)
    unrelated_hash = str(imagehash.phash(unrelated_img))
    rows2 = sqlite3.connect(DB_PATH).execute(
        "SELECT video_id, hash_value FROM fingerprints"
    ).fetchall()
    dist2 = min(
        imagehash.hex_to_hash(unrelated_hash) - imagehash.hex_to_hash(h)
        for _, h in rows2
    )
    print(f"   Hamming dist  : {dist2}")
    print(f"   Result        : {'FALSE POSITIVE ✗' if dist2 <= THRESHOLD else 'Correctly rejected ✓'}")

    # Cleanup
    os.remove(DB_PATH)
    print("\nTest database cleaned up.")
    print("=" * 55)


if __name__ == "__main__":
    test_store_and_match()
