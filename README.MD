**Warning!**

This application is 100% vibe coded. I only briefly checked that it does not hammer the sites it scrapes, and I run it once a day.

## About

Simple watcher for my dream bike. It writes a static HTML report: **New** (unseen listings) and **All** (everything already stored). Favorites are saved in the browser, not in the repo.

Needs Python 3.11+.

## Install and run

From the repo directory:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m bike_scraper
```

Open `data/report.html` in a browser.

Run again with `.venv/bin/python -m bike_scraper`. Add `--open` to open the report afterwards. `--once-a-day` skips the scrape if it already ran today.

## Cron (optional)

I use this user crontab line (`[path]` is the repo directory):

```cron
@reboot sleep 30 && [path]/.venv/bin/python -m bike_scraper --once-a-day
```

It runs on boot. `--once-a-day` skips a second run the same day.

## Reset the database

Delete `data/seen.db`, or run:

```bash
.venv/bin/python -m bike_scraper --reset
```

The next scrape recreates an empty database. Everything currently listed will show up under **New** again. Favorites in the browser are not cleared.
