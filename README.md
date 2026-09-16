# Oxford Busy Diary

A local diary aid for Graham at The Plough Inn, 38 Cornmarket Street, Oxford OX1 3HA. It checks public Oxford event pages for potential busy dates: conferences, degree ceremonies, open days, Oxford Open Doors, home football fixtures, theatre, city festivals, major road events and more. It is a lead finder, not a forecast. Check the organiser's page before changing staffing or placing orders. Private bookings may never be published.

## Run with Docker on a laptop

1. Install Docker Desktop and start it.
2. Unzip this package into a folder.
3. Copy `.env.example` to `.env`. Set a real contact address in `USER_AGENT` so site operators can reach you.
4. From that folder, run `docker compose up -d --build`.
5. Open `http://localhost:8080`, open **Sources**, and start a scan. The first scan can take a while because requests are deliberately spaced out. Sources with a robots block or a changed page are shown in Source health. A source marked **empty** was reachable but produced no future dated events, which may be normal or may mean its page layout changed.
6. When finished, run `docker compose down`. Your data stays in `./data/tracker.sqlite3`.

If you leave the app running, it scans again every `SCAN_INTERVAL_HOURS` (default 24). Starting the app does not itself start a scan; use the button when you need fresh information.

The supplied Compose file binds to localhost. The app has no sign-in screen, so do not expose it directly to the internet. Back up the SQLite file to preserve review decisions and source edits.


## Build directly from GitHub

Keep `compose.git.yaml` and your local `.env` in one laptop folder. Run `docker compose -f compose.git.yaml up -d --build` to fetch the latest `main` branch and start the app. Run `docker compose -f compose.git.yaml down` when finished. The `./data` folder beside the Compose file holds your diary and review decisions across rebuilds. The regular `compose.yaml` still builds from a local copy of the app.

A public repository needs no Git authentication for the remote build. If the repository is private, configure Git authentication for Docker's remote Git build context first; otherwise clone/pull it locally and use `compose.yaml`. Docker Compose follows the [Git build context format](https://docs.docker.com/reference/compose-file/build/).

## What is tracked

- **Generic public events:** Schema.org `Event` JSON-LD and public event cards with machine-readable dates or clearly printed dates. The crawler follows event-related links on the same host, up to `MAX_PAGES_PER_SOURCE`.
- **Dedicated readers:** the official Oxford United men's fixtures page (home games at the Kassam only), Oxford degree ceremonies (in-person dates only), Oxford main term and full-term dates, New Theatre Oxford listings, and the county's Oxford-related large-public-event road notices. Readers use public HTML and may need updates when a site changes its layout.
- **Review and exports:** filter by date, venue, type, confidence and status; approve or ignore leads; export CSV or an all-day ICS calendar. The page records source URL and when it was last checked. Rescans flag changed details and return a changed approved item to New.
- **Dates to watch:** an indicative 0–100 signal combines distinct events on the same date. City-centre venues receive more weight; Oxford United home games remain strong signals despite the stadium's distance. Road notices appear as access alerts and do not increase the busy score. This score is a triage aid, not a prediction of sales or attendance.
- **Travel checks:** the dashboard links to live Oxford Bus, GWR and National Rail service pages. These are manual checks; the app does not currently import transport alerts automatically.

Attendance is recorded only when a page publishes a capacity figure, which can differ from actual attendance. Theatre listing dates may show the first day of a run rather than every performance; check show times on the linked page. Football kick-off times can move, so rescan before match day. Source listings vary in quality and may show zero events despite being reachable.

## Sources and configuration

The registry starts with Oxford Events (the University’s current central listing), Oxford colleges, departments and institutes, city listings, nearby theatres, Oxford United, Oxford Brookes graduation, Oxford Pride, May Morning and other public pages. It is a starting list, not a guarantee that every URL is a working calendar. You can edit URLs, enable or disable sources and choose a reader on the **Sources** page. New seed sources are added to an existing database on upgrade without replacing edited entries.

See `.env.example`. `REQUEST_DELAY_SECONDS` has a minimum of 1 second. `MAX_PAGES_PER_SOURCE` is capped at 30; set it to 3 for a faster first pass. `SCAN_INTERVAL_HOURS` controls rescans while the app is running.

## Crawling limits

The crawler checks robots.txt before fetching a page, uses a descriptive user agent, spaces requests per host, caps pages and reports errors. It does not log in, solve CAPTCHAs, bypass paywalls or attempt to discover private bookings. A 403/406 response to robots.txt is treated as blocked; the app does not try another route around it. Site terms may impose further restrictions even when robots.txt allows access: check terms before enabling a source and disable any source that prohibits this use. Avoid reposting event descriptions or using this tool as a substitute for organisers' listings.

## Development

With Python 3.12, install `requirements.txt` in a virtual environment and run `python -m app.main`. The app uses Flask, SQLite, Beautiful Soup, Requests and APScheduler. Run one app process per database because scheduling is in-process.

## Source references

The seed registry uses the [Oxford central events page](https://www.ox.ac.uk/events), [college directory](https://www.ox.ac.uk/colleges), [degree ceremony schedule](https://www.ox.ac.uk/students/graduation/ceremonies), [term dates](https://www.ox.ac.uk/about/the-university/facts-and-figures/dates-of-term), [official Oxford United fixtures](https://www.oufc.co.uk/fixture/list/62), [New Theatre listings](https://www.atgtickets.com/venues/new-theatre-oxford/whats-on/) and [Oxfordshire large public events](https://www.oxfordshire.gov.uk/business/licences-and-permits/licences-and-permits/large-public-events), among other public pages.
