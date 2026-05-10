"""
demo_service.py
───────────────
Manages admin-uploaded preview videos.
Each preview slot (1–4) has a Telegram file_id and a per-video star price.
"""

from services.database import get_db_connection


def set_demo_video(slot: int, file_id: str, price: int, title: str = None, video_type: str = 'regular', duration: int = None) -> None:
    """Insert or replace a demo video for the given slot."""
    conn = get_db_connection()
    conn.execute(
        '''INSERT INTO demo_videos (slot, file_id, price, title, video_type, duration, uploaded_at)
           VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(slot) DO UPDATE SET
               file_id     = excluded.file_id,
               price       = excluded.price,
               title       = excluded.title,
               video_type  = excluded.video_type,
               duration    = excluded.duration,
               uploaded_at = excluded.uploaded_at''',
        (slot, file_id, price, title, video_type, duration)
    )
    conn.commit()
    conn.close()


def get_demo_video(slot: int) -> dict | None:
    """Return the demo video record for a slot, or None if not set."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM demo_videos WHERE slot = ?", (slot,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_demo_videos() -> list[dict]:
    """Return all uploaded demo videos ordered by slot number."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM demo_videos ORDER BY slot"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_next_slot() -> int:
    """Return the next available slot number (max slot + 1, or 1 if empty)."""
    conn = get_db_connection()
    row = conn.execute("SELECT MAX(slot) as max_slot FROM demo_videos").fetchone()
    conn.close()
    max_slot = row["max_slot"] if row and row["max_slot"] is not None else 0
    return max_slot + 1


def get_random_video_by_type(video_type: str) -> dict | None:
    """Return a random demo video for a given type."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM demo_videos WHERE video_type = ? ORDER BY RANDOM() LIMIT 1", (video_type,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_demo_video(slot: int) -> bool:
    """Remove a demo video from a slot. Returns True if a row was deleted."""
    conn = get_db_connection()
    cursor = conn.execute("DELETE FROM demo_videos WHERE slot = ?", (slot,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted
