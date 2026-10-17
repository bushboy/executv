"""Emit mock Ring / site / delivery events into core_engine without physical hardware.

Usage:
    uv run python scripts/seed_ring_events.py
    uv run python scripts/seed_ring_events.py --url http://127.0.0.1:8001
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SAMPLES = [
    {
        "source": "ring_site_gateway",
        "event_type": "freight_backlog",
        "location": "Warehouse 4 — Gate 4",
        "description": (
            "Ring camera at Gate 4 shows a freight truck backlog blocking the physical inventory audit."
        ),
        "priority": "HIGH",
        "image_url": (
            "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=800&auto=format&fit=crop"
        ),
    },
]


def _post(url: str, body: dict) -> dict:
    payload = dict(body)
    payload.setdefault("occurred_at", datetime.now(timezone.utc).isoformat())
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Push mock Ring operational events to ExecuTV.")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8001/api/v1/events/ingest",
        help="Ingest webhook URL",
    )
    args = parser.parse_args()

    for sample in SAMPLES:
        try:
            result = _post(args.url, sample)
        except HTTPError as exc:
            print(f"FAIL {sample['location']}: HTTP {exc.code} {exc.read().decode('utf-8', 'replace')}", file=sys.stderr)
            return 1
        except URLError as exc:
            print(f"FAIL {sample['location']}: {exc.reason}", file=sys.stderr)
            return 1
        print(
            f"OK  {sample['source']:<8} {sample['location']} -> "
            f"{result.get('status')} {result.get('event_id')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
