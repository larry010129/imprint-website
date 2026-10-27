"""Weekly site report CLI -> Discord webhook.

  python scripts/weekly_report.py             # send last Mon-Sun (Taipei) report
  python scripts/weekly_report.py --dry-run   # print the payload, send nothing
  python scripts/weekly_report.py --on-deploy # Render pre-deploy: send only when
                                              # REPORT_ON_DEPLOY=1 is set

Never exits non-zero, so it cannot block a Render deploy. The Monday 09:00
schedule is run by the app itself (app/weekly_report.py: report_loop).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.weekly_report import TAIPEI, build_report, send, webhook_url, week_bounds  # noqa: E402

log = logging.getLogger("weekly_report")


def run(argv: list[str]) -> None:
    dry = "--dry-run" in argv
    if "--on-deploy" in argv and os.environ.get("REPORT_ON_DEPLOY") != "1":
        print("weekly_report: REPORT_ON_DEPLOY not set, skipping")
        return
    url = webhook_url()
    if not url and not dry:
        print("weekly_report: DISCORD_REPORT_WEBHOOK_URL not set, skipping")
        return
    end = week_bounds(datetime.now(TAIPEI).date())[2]
    payload, png = build_report(end)
    if dry:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"chart: {'%d bytes' % len(png) if png else 'none'}")
        return
    send(payload, url, png)
    print(f"weekly_report: sent report for {end - timedelta(days=7)} to {end - timedelta(days=1)}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        run(sys.argv[1:])
    except Exception:
        # Never fail the deploy over a report.
        log.exception("weekly_report failed")
    sys.exit(0)
