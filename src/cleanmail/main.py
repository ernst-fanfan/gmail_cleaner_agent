from __future__ import annotations

import argparse
import logging
from datetime import datetime, time as dtime
from typing import Callable, Dict, Any

from .config import load_config
from .logging_setup import setup_logging
from .engine import process_inbox
from .reporter import build_markdown_report, save_report
from .scheduler import start_scheduler, run_once
from .gmail_client import RealGmailGateway


log = logging.getLogger(__name__)


def _runner_factory(cfg: Dict[str, Any], *, use_gmail: bool = False) -> Callable[[datetime], None]:
    def _runner(now: datetime) -> None:
        gateway = None
        if use_gmail:
            gateway = RealGmailGateway()
            creds_dir = cfg.get("secrets", {}).get("google_credentials_dir")
            try:
                gateway.authenticate(creds_dir)
            except Exception as e:
                log.error("Gmail authentication failed: %s", e)
        report = process_inbox(now, cfg, gateway=gateway)
        md = build_markdown_report(report, cfg)
        # Save report
        save_dir = cfg.get("report", {}).get("save_dir")
        ts = now.strftime("%Y-%m-%d")
        path = f"{save_dir}/{ts}.md"
        save_report(md, path)
        log.info("Report written to %s", path)
    return _runner


def main() -> None:
    """CLI entrypoint.

    - Loads config and initializes logging.
    - Supports `run` (one-off), and `serve` (start scheduler) subcommands.
    """
    parser = argparse.ArgumentParser(prog="cleanmail")
    parser.add_argument("command", choices=["run", "serve", "healthcheck"], help="What to do")
    parser.add_argument("--config", dest="config", default=None, help="Path to config.yaml")
    parser.add_argument("-v", dest="verbosity", action="count", default=0, help="Increase verbosity")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Force dry run")
    parser.add_argument("--use-gmail", dest="use_gmail", action="store_true", help="Use real Gmail gateway (experimental)")

    args = parser.parse_args()
    setup_logging(args.verbosity)
    cfg = load_config(args.config)
    if args.dry_run:
        cfg.setdefault("mode", {})["dry_run"] = True

    if args.command == "healthcheck":
        print("ok")
        return

    runner = _runner_factory(cfg, use_gmail=bool(args.use_gmail))

    if args.command == "run":
        tz = cfg.get("schedule", {}).get("timezone", "UTC")
        run_once(runner, tz)
    elif args.command == "serve":
        sched = cfg.get("schedule", {})
        hh, mm = map(int, str(sched.get("time", "22:00")).split(":"))
        tz = sched.get("timezone", "UTC")
        start_scheduler(daily_time=dtime(hour=hh, minute=mm), timezone=tz, runner=runner)


if __name__ == "__main__":
    main()
