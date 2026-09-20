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

## GitHub Actions (optional)

The workflow in `.github/workflows/scrape.yml` scrapes once a day (06:00 UTC) and can be started by hand from the Actions tab. `seen.db` is kept on a `data` branch so later runs still know which listings you have already seen. The HTML report is published with GitHub Pages.

After you push the workflow:

1. Repo **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Run **Scrape and publish** once from the Actions tab (first run may ask you to approve the `github-pages` environment)
3. Open `https://<user>.github.io/bike_scraper/`

GitHub runner IPs get blocked more often than a home machine. Favorites on the Pages site are stored in that browser, separate from a local `file://` report.
