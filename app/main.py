import csv
import io
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from apscheduler.schedulers.background import BackgroundScheduler
from bs4 import BeautifulSoup
from dateutil import parser as dateparser
from flask import Flask, Response, abort, redirect, render_template, request, url_for

from .seed import SOURCES
from .adapters import ADAPTERS

app = Flask(__name__, template_folder='../templates', static_folder='../static')
DATA_DIR = os.getenv('DATA_DIR', 'data')
os.makedirs(DATA_DIR, exist_ok=True)
DB = os.path.join(DATA_DIR, 'tracker.sqlite3')
AGENT = os.getenv('USER_AGENT', 'OxfordConferenceTracker/1.0 (+contact: local-operator)')
DELAY = max(1.0, float(os.getenv('REQUEST_DELAY_SECONDS', '3')))
MAX_PAGES = min(30, max(1, int(os.getenv('MAX_PAGES_PER_SOURCE', '12'))))
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': AGENT, 'Accept': 'text/html,application/ld+json'})
last_request = {}
robots_cache = {}
scan_lock = threading.Lock()
TYPES = {'conference': r'conference|congress|summit|convention|forum', 'symposium': r'symposium|colloquium', 'workshop': r'workshop|masterclass|training|summer school', 'graduation': r'graduation|degree ceremony', 'open doors': r'open doors|heritage open', 'open day': r'open day|open evening|applicant day|visiting day', 'home match': r'home match|oxford united v ', 'term date': r'term start|term end', 'festival': r'festival|carnival|fair|fayre', 'performance': r'concert|performance|theatre|musical|comedy|opera|show', 'public event': r'exhibition|tour|community event|market|parade|celebration|race|marathon|pride', 'other academic': r'lecture|seminar|research day|academic event'}
LINK_HINT = re.compile('|'.join(TYPES.values()) + r'|/events?/|/what.s.on/', re.I)


def conn():
    db = sqlite3.connect(DB, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL')
    return db


def init_db():
    with conn() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS sources (id INTEGER PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL UNIQUE, kind TEXT NOT NULL DEFAULT 'listing', enabled INTEGER NOT NULL DEFAULT 1, last_checked TEXT, last_success TEXT, health TEXT DEFAULT 'new', error TEXT, pages_checked INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, dedupe_key TEXT NOT NULL UNIQUE, title TEXT NOT NULL, start TEXT NOT NULL, end TEXT, venue TEXT, organiser TEXT, event_type TEXT, attendance INTEGER, public_clue TEXT, source_url TEXT NOT NULL, source_id INTEGER, last_checked TEXT, first_seen TEXT, updated_at TEXT, status TEXT NOT NULL DEFAULT 'new', confidence REAL, relevance REAL, change_note TEXT);
        CREATE TABLE IF NOT EXISTS sightings (id INTEGER PRIMARY KEY, event_id INTEGER NOT NULL, source_id INTEGER NOT NULL, url TEXT NOT NULL, seen_at TEXT NOT NULL, UNIQUE(event_id,url));
        CREATE INDEX IF NOT EXISTS idx_events_start ON events(start);
        ''')
        db.executemany('INSERT OR IGNORE INTO sources(name,url,kind) VALUES(?,?,?)', SOURCES)


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def allowed(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return False, 'Only public HTTP(S) URLs are supported'
    root = f'{parsed.scheme}://{parsed.netloc}'
    if root not in robots_cache:
        rp = RobotFileParser()
        rp.set_url(root + '/robots.txt')
        try:
            response = SESSION.get(root + '/robots.txt', timeout=12)
            if response.status_code == 404:
                rp.parse([])
            elif response.ok:
                rp.parse(response.text.splitlines())
            else:
                return False, f'robots.txt returned HTTP {response.status_code}'
        except requests.RequestException as e:
            return False, f'robots.txt unavailable: {e}'
        robots_cache[root] = rp
    return robots_cache[root].can_fetch(AGENT, url), 'Disallowed by robots.txt'


def fetch(url):
    ok, reason = allowed(url)
    if not ok:
        raise RuntimeError(reason)
    host = urlparse(url).netloc
    pause = DELAY - (time.monotonic() - last_request.get(host, -DELAY))
    if pause > 0:
        time.sleep(pause)
    last_request[host] = time.monotonic()
    response = SESSION.get(url, timeout=20, allow_redirects=True)
    response.raise_for_status()
    if urlparse(response.url).netloc != host:
        ok, reason = allowed(response.url)
        if not ok:
            raise RuntimeError('Redirect target: ' + reason)
    if 'html' not in response.headers.get('Content-Type', ''):
        raise RuntimeError('Non-HTML response')
    return response.text, response.url


def date_value(value):
    if isinstance(value, dict):
        value = value.get('@value') or value.get('date')
    if not value:
        return None
    try:
        raw = str(value)
        dt = dateparser.isoparse(raw) if re.match(r'^\d{4}-\d{2}-\d{2}', raw) else dateparser.parse(raw, fuzzy=False, dayfirst=True)
        if dt and dt.year >= datetime.now().year - 1:
            return dt.isoformat(timespec='minutes')
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def plain(value):
    if isinstance(value, dict):
        return value.get('name') or value.get('address', {}).get('streetAddress', '') if isinstance(value.get('address'), dict) else value.get('name', '')
    if isinstance(value, list):
        return ', '.join(filter(None, (plain(v) for v in value)))
    return str(value or '').strip()


def classify(title, description=''):
    text = (title + ' ' + description).lower()
    for kind, pattern in TYPES.items():
        if re.search(pattern, text, re.I):
            return kind
    return 'other academic'


def walk_json(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from walk_json(item)
    elif isinstance(obj, dict):
        typ = obj.get('@type', '')
        if 'Event' in typ if isinstance(typ, str) else 'Event' in typ:
            yield obj
        for key in ('@graph', 'itemListElement', 'mainEntity'):
            if key in obj:
                yield from walk_json(obj[key])


def extract(html, url, source):
    soup = BeautifulSoup(html, 'html.parser')
    found = []
    for tag in soup.find_all('script', type='application/ld+json'):
        try:
            for item in walk_json(json.loads(tag.string or tag.get_text())):
                start = date_value(item.get('startDate'))
                title = plain(item.get('name'))
                if start and title:
                    desc = plain(item.get('description'))
                    attendance = item.get('maximumAttendeeCapacity') or item.get('remainingAttendeeCapacity')
                    try: attendance = int(attendance)
                    except (ValueError, TypeError): attendance = None
                    found.append(dict(title=title, start=start, end=date_value(item.get('endDate')), venue=plain(item.get('location')) or source['name'], organiser=plain(item.get('organizer')) or source['name'], event_type=classify(title, desc), attendance=attendance, public_clue=plain(item.get('eventAttendanceMode') or item.get('isAccessibleForFree')), source_url=urljoin(url, plain(item.get('url')) or url), evidence='structured'))
        except (ValueError, TypeError):
            pass
    # A conservative HTML fallback: only event/article cards with a machine-readable time element.
    for card in soup.select('article, .event, .event-card, [class*="event-item"]'):
        t = card.find('time', datetime=True)
        heading = card.find(['h1','h2','h3','h4'])
        if not t or not heading:
            continue
        start = date_value(t.get('datetime'))
        title = heading.get_text(' ', strip=True)
        if not start or not title:
            continue
        a = heading.find('a', href=True) or card.find('a', href=True)
        found.append(dict(title=title, start=start, end=None, venue=source['name'], organiser=source['name'], event_type=classify(title), attendance=None, public_clue='', source_url=urljoin(url, a['href']) if a else url, evidence='html'))
    return found, soup


def key_for(event):
    title = re.sub(r'[^a-z0-9]+', ' ', event['title'].lower()).strip()
    if event['event_type'] == 'home match':
        return title + '|' + event['start'][:4]
    return title + '|' + event['start'][:10]


def save_event(db, event, source_id):
    key = key_for(event)
    old = db.execute('SELECT * FROM events WHERE dedupe_key=?', (key,)).fetchone()
    event['confidence'] = {'structured': .9, 'adapter': .8, 'html': .65}[event['evidence']]
    event['relevance'] = {'conference': 1, 'symposium': .9, 'graduation': .95, 'open doors': .9, 'open day': .85, 'home match': .9, 'term date': .5, 'festival': .85, 'performance': .7, 'public event': .6, 'access alert': 0, 'workshop': .7, 'other academic': .35}[event['event_type']]
    if event['attendance']:
        event['relevance'] = min(1, event['relevance'] + .1)
    fields = ['title','start','end','venue','organiser','event_type','attendance','public_clue','source_url','confidence','relevance']
    if old:
        changed = [f for f in fields if old[f] != event[f]]
        note = 'Changed: ' + ', '.join(changed) if changed else old['change_note']
        status = 'new' if changed and old['status'] == 'approved' else old['status']
        db.execute('UPDATE events SET title=?,start=?,end=?,venue=?,organiser=?,event_type=?,attendance=?,public_clue=?,source_url=?,confidence=?,relevance=?,last_checked=?,updated_at=?,change_note=?,status=? WHERE id=?', tuple(event[f] for f in fields) + (now(), now() if changed else old['updated_at'], note, status, old['id']))
        event_id = old['id']
    else:
        db.execute('INSERT INTO events(dedupe_key,title,start,end,venue,organiser,event_type,attendance,public_clue,source_url,confidence,relevance,source_id,last_checked,first_seen,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', (key,) + tuple(event[f] for f in fields) + (source_id,now(),now(),now()))
        event_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
    db.execute('INSERT INTO sightings(event_id,source_id,url,seen_at) VALUES(?,?,?,?) ON CONFLICT(event_id,url) DO UPDATE SET seen_at=excluded.seen_at', (event_id,source_id,event['source_url'],now()))


def scan_source(source_id):
    with conn() as db:
        source = db.execute('SELECT * FROM sources WHERE id=?', (source_id,)).fetchone()
        if not source or not source['enabled']:
            return
        pages = [source['url']]
        seen = set()
        count = 0
        found = 0
        try:
            while pages and count < MAX_PAGES:
                url = pages.pop(0)
                if url in seen or urlparse(url).netloc != urlparse(source['url']).netloc:
                    continue
                seen.add(url)
                html, final_url = fetch(url)
                count += 1
                if source['kind'] in ADAPTERS:
                    events = ADAPTERS[source['kind']](html, final_url)
                    soup = BeautifulSoup(html, 'html.parser')
                else:
                    events, soup = extract(html, final_url, source)
                for event in events:
                    if event['start'][:10] >= datetime.now().date().isoformat():
                        save_event(db, event, source_id)
                        found += 1
                if count == 1 and source['kind'] == 'listing':
                    for a in soup.find_all('a', href=True):
                        href = urljoin(final_url, a['href']).split('#')[0]
                        if urlparse(href).netloc == urlparse(source['url']).netloc and LINK_HINT.search(href + ' ' + a.get_text(' ', strip=True)) and href not in seen and href not in pages:
                            pages.append(href)
                db.commit()
            db.execute('UPDATE sources SET last_checked=?,last_success=?,health=?,error=NULL,pages_checked=? WHERE id=?', (now(),now(),f'ok · {found} events',count,source_id))
        except Exception as e:
            db.execute('UPDATE sources SET last_checked=?,health=?,error=?,pages_checked=? WHERE id=?', (now(),'blocked' if 'robots' in str(e).lower() else 'error',str(e)[:400],count,source_id))
        db.commit()


def scan_all():
    if not scan_lock.acquire(blocking=False):
        return
    try:
        with conn() as db:
            ids = [r[0] for r in db.execute('SELECT id FROM sources WHERE enabled=1')]
        for source_id in ids:
            scan_source(source_id)
    finally:
        scan_lock.release()


def filtered_events():
    clauses = ['1=1']
    args = []
    if not request.args.get('from'):
        clauses.append('start >= ?')
        args.append(datetime.now().date().isoformat())
    for param, column, op in [('from','start','>='),('to','start','<'),('type','event_type','='),('status','status','='),('venue','venue','LIKE')]:
        val = request.args.get(param, '').strip()
        if val:
            if param == 'to': val += 'T23:59:59'
            if param == 'venue': val = '%' + val + '%'
            clauses.append(f'{column} {op} ?')
            args.append(val)
    if request.args.get('confidence'):
        clauses.append('confidence >= ?')
        args.append(float(request.args['confidence']))
    with conn() as db:
        return db.execute('SELECT * FROM events WHERE ' + ' AND '.join(clauses) + ' ORDER BY start LIMIT 2000', args).fetchall()


def proximity(event):
    """Broad location bands around 38 Cornmarket Street; deliberately approximate."""
    venue = (event['venue'] or '').lower()
    if event['event_type'] == 'home match':
        return 1.0, 'Home match'
    if any(x in venue for x in ('new theatre', 'playhouse', 'sheldonian', 'broad street', 'cornmarket', 'town hall', 'city centre')):
        return 1.0, 'City centre'
    if any(x in venue for x in ('kassam', 'headington', 'brookes', 'cowley')):
        return .6, 'Across Oxford'
    return .75, 'Oxford'


def busy_days(events):
    days = {}
    for event in events:
        if event['status'] == 'ignored' or event['event_type'] == 'access alert':
            continue
        day = event['start'][:10]
        weight, area = proximity(event)
        item = days.setdefault(day, {'date': day, 'score': 0, 'count': 0, 'reasons': [], 'areas': set()})
        item['score'] += round(42 * event['relevance'] * weight * event['confidence'])
        item['count'] += 1
        item['areas'].add(area)
        if len(item['reasons']) < 3:
            item['reasons'].append(event['title'])
    for item in days.values():
        item['score'] = min(100, item['score'] + min(25, (item['count'] - 1) * 8))
        item['level'] = 'Slammed watch' if item['score'] >= 70 else 'Busy watch' if item['score'] >= 40 else 'Worth noting'
        item['areas'] = ', '.join(sorted(item['areas']))
    return sorted(days.values(), key=lambda d: (-d['score'], d['date']))[:10]


@app.route('/')
def index():
    events = filtered_events()
    today = datetime.now().date().isoformat()
    with conn() as db:
        stats = {k: db.execute(q).fetchone()[0] for k,q in {'sources':'SELECT COUNT(*) FROM sources','upcoming':'SELECT COUNT(*) FROM events WHERE start>=date("now")','review':'SELECT COUNT(*) FROM events WHERE status="new" AND start>=date("now")','errors':'SELECT COUNT(*) FROM sources WHERE health IN ("error","blocked")'}.items()}
    return render_template('index.html', events=events, stats=stats, today=today, filters=request.args, busy=busy_days(events))


@app.route('/sources')
def sources():
    with conn() as db:
        rows = db.execute('SELECT * FROM sources ORDER BY name').fetchall()
    return render_template('sources.html', sources=rows)


@app.post('/sources')
def add_source():
    name = request.form.get('name','').strip()
    url = request.form.get('url','').strip()
    if not name or not url or urlparse(url).scheme not in ('http','https'):
        abort(400)
    with conn() as db:
        kind = request.form.get('kind','listing')
        if kind not in ('listing', *ADAPTERS):
            abort(400)
        db.execute('INSERT OR IGNORE INTO sources(name,url,kind) VALUES(?,?,?)', (name,url,kind))
    return redirect(url_for('sources'))


@app.post('/sources/<int:source_id>')
def edit_source(source_id):
    with conn() as db:
        if request.form.get('action') == 'scan':
            threading.Thread(target=scan_source, args=(source_id,), daemon=True).start()
        else:
            name = request.form.get('name','').strip()
            url = request.form.get('url','').strip()
            if not name or urlparse(url).scheme not in ('http','https'):
                abort(400)
            kind = request.form.get('kind','listing')
            if kind not in ('listing', *ADAPTERS):
                abort(400)
            db.execute('UPDATE sources SET name=?,url=?,kind=?,enabled=? WHERE id=?', (name,url,kind,1 if request.form.get('enabled') else 0,source_id))
    return redirect(url_for('sources'))


@app.post('/scan')
def trigger_scan():
    threading.Thread(target=scan_all, daemon=True).start()
    return redirect(url_for('sources'))


@app.post('/events/<int:event_id>/status')
def event_status(event_id):
    status = request.form.get('status')
    if status not in ('new','approved','ignored'):
        abort(400)
    with conn() as db:
        db.execute('UPDATE events SET status=? WHERE id=?', (status,event_id))
    return redirect(request.referrer or url_for('index'))


@app.route('/export.csv')
def export_csv():
    out = io.StringIO()
    writer = csv.writer(out)
    columns = ['title','start','end','venue','organiser','event_type','attendance','public_clue','source_url','last_checked','status','confidence','relevance','change_note']
    writer.writerow(columns)
    for row in filtered_events():
        writer.writerow([row[c] for c in columns])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition':'attachment; filename=oxford-events.csv'})


def ics_escape(value):
    return str(value or '').replace('\\','\\\\').replace('\n','\\n').replace(',','\\,').replace(';','\\;')


@app.route('/export.ics')
def export_ics():
    lines = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Plough Inn//Oxford Conference Tracker//EN','CALSCALE:GREGORIAN']
    for row in filtered_events():
        start = row['start']
        date = start[:10].replace('-','')
        lines += ['BEGIN:VEVENT',f'UID:oxford-tracker-{row["id"]}@plough.local',f'DTSTAMP:{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")}',f'DTSTART;VALUE=DATE:{date}',f'DTEND;VALUE=DATE:{(datetime.fromisoformat(start[:10]) + timedelta(days=1)).strftime("%Y%m%d")}',f'SUMMARY:{ics_escape(row["title"])}',f'LOCATION:{ics_escape(row["venue"])}',f'DESCRIPTION:{ics_escape(row["event_type"] + " | " + row["status"])}',f'URL:{row["source_url"]}','END:VEVENT']
    lines.append('END:VCALENDAR')
    return Response('\r\n'.join(lines)+'\r\n', mimetype='text/calendar', headers={'Content-Disposition':'attachment; filename=oxford-events.ics'})


init_db()
if __name__ == '__main__':
    scheduler = BackgroundScheduler()
    interval_hours = max(1, int(os.getenv('SCAN_INTERVAL_HOURS','24')))
    scheduler.add_job(scan_all, 'interval', hours=interval_hours, next_run_time=datetime.now()+timedelta(hours=interval_hours), max_instances=1)
    scheduler.start()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT','8080')), use_reloader=False)
