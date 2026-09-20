from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from bike_scraper.runner import already_ran_today, reset_data, run


def main() -> None:
    parser = argparse.ArgumentParser(description="Check watched bike listings and write an HTML report.")
    parser.add_argument("--config", type=Path, help="Path to config.toml")
    parser.add_argument("--all", action="store_true", help="List every current match, not only new ones")
    parser.add_argument("--query", help="Override the search query (useful for a one-off check)")
    parser.add_argument("--open", action="store_true", help="Open the HTML report after scraping")
    parser.add_argument("--reset", action="store_true", help="Delete the database and thumbnails, then exit")
    parser.add_argument(
        "--once-a-day",
        action="store_true",
        help="Skip scraping if a successful run already happened today",
    )
    args = parser.parse_args()

    if args.reset:
        report = reset_data(args.config)
        print(f"Database reset. Empty report: {report}")
        return

    if args.once_a_day and already_ran_today(args.config):
        print("Already ran today; leaving the existing report as-is.")
        return

    result = run(config_path=args.config, show_all=args.all, query_override=args.query)
    print(result.text)
    if args.open:
        webbrowser.open(result.report_path.as_uri())


if __name__ == "__main__":
    main()
