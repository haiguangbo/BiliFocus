from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "apps" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import Settings  # noqa: E402
from app.providers.factory import SearchProviderFactory  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download one Bilibili video to a local MP4 file.")
    parser.add_argument("bvid", help="Target Bilibili BV id, for example BV1zV2QBtE39")
    parser.add_argument("--quality", default=None, help="Optional quality code, for example 64 or 16")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for the downloaded MP4 file",
    )
    return parser.parse_args()


def sanitize_filename(value: str) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    return re.sub(r'[\\/:*?"<>|]+', "_", compact)[:120] or "video"


def load_bilibili_cookie(settings: Settings) -> str:
    database_path = settings.database_path
    if not database_path.exists():
        return ""
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT bilibili_cookie FROM user_preferences WHERE singleton_key = 'default' LIMIT 1"
        ).fetchone()
    if not row:
        return ""
    return str(row[0] or "")


def load_download_output_dir(settings: Settings) -> str:
    database_path = settings.database_path
    if not database_path.exists():
        return str(REPO_ROOT / "data" / "downloads")
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            "SELECT download_output_dir FROM user_preferences WHERE singleton_key = 'default' LIMIT 1"
        ).fetchone()
    if not row or not row[0]:
        return str(REPO_ROOT / "data" / "downloads")
    configured = Path(str(row[0])).expanduser()
    if configured.is_absolute():
        return str(configured)
    return str((REPO_ROOT / configured).resolve())


def main() -> int:
    args = parse_args()
    settings = Settings(_env_file=str(BACKEND_ROOT / ".env"))
    try:
        bilibili_cookie = load_bilibili_cookie(settings)
        provider = SearchProviderFactory(settings, bilibili_cookie=bilibili_cookie).resolve("default")
        detail = provider.get_video(args.bvid)
        if detail is None:
            print(f"video not found: {args.bvid}", file=sys.stderr)
            return 1

        playback = provider.get_playback_source(args.bvid, quality_code=args.quality)
        if playback is None:
            print(f"playback source unavailable: {args.bvid}", file=sys.stderr)
            return 1

        output_dir = Path(args.output_dir or load_download_output_dir(settings)).expanduser()
        if not output_dir.is_absolute():
            output_dir = (REPO_ROOT / output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{sanitize_filename(detail.title)}-{playback.selected_quality_label or playback.selected_quality_code}.mp4"
        target = output_dir / filename

        stream, _, _ = provider.stream_playback_source(playback)
        total_bytes = 0
        with target.open("wb") as handle:
            for chunk in stream:
                handle.write(chunk)
                total_bytes += len(chunk)

        print(
            {
                "bvid": args.bvid,
                "title": detail.title,
                "quality_code": playback.selected_quality_code,
                "quality_label": playback.selected_quality_label,
                "output": str(target),
                "bytes_written": total_bytes,
                "auth_cookie_loaded": bool(bilibili_cookie),
            }
        )
        return 0
    finally:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
