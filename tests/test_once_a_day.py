from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from bike_scraper.config import load_config
from bike_scraper.runner import already_ran_today, mark_ran_today, reset_data


def _config(tmp: str) -> Path:
    path = Path(tmp) / "config.toml"
    path.write_text(
        f'''
database = "{Path(tmp) / "seen.db"}"
report = "{Path(tmp) / "report.html"}"
thumbs = "{Path(tmp) / "thumbs"}"
request_delay_seconds = 0.1

[[searches]]
site = "bikemaster"
query = "agusta"
''',
        encoding="utf-8",
    )
    return path


class OnceADayTests(unittest.TestCase):
    def test_stamp_is_today_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(tmp)
            self.assertFalse(already_ran_today(config))
            mark_ran_today(config)
            self.assertTrue(already_ran_today(config))
            stamp = load_config(config).database
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            Path(stamp).with_name("last_run").write_text(yesterday + "\n", encoding="utf-8")
            self.assertFalse(already_ran_today(config))

    def test_reset_clears_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = _config(tmp)
            mark_ran_today(config)
            reset_data(config)
            self.assertFalse(already_ran_today(config))
