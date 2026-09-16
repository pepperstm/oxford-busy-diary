"""Small, conservative readers for public pages with recurring list formats."""
import re
from datetime import date, datetime, timedelta
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

DATE_LINE = re.compile(r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+[A-Za-z]+(?:\s+\d{4})?$', re.I)
SHORT_DATE = re.compile(r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$', re.I)


def _future_date(label):
    try:
        dt = dateparser.parse(label, fuzzy=False, dayfirst=True, default=datetime(date.today().year, 1, 1))
    except (ValueError, TypeError):
        return None
    if not re.search(r'\b20\d{2}\b', label) and dt.date() < date.today() - timedelta(days=14):
        dt = dt.replace(year=dt.year + 1)
    return dt.date().isoformat() if dt.date() >= date.today() else None


def _base(title, start, venue, url, event_type, clue=''):
    return dict(title=title, start=start, end=None, venue=venue, organiser=venue,
                event_type=event_type, attendance=None, public_clue=clue,
                source_url=url, evidence='adapter')


def fixtures(html, url):
    """The official OUFC page groups each fixture under a weekday heading."""
    soup = BeautifulSoup(html, 'html.parser')
    lines = [s.strip() for s in soup.get_text('\n').splitlines() if s.strip()]
    starts = [i for i, line in enumerate(lines) if DATE_LINE.fullmatch(line)]
    results = []
    for n, i in enumerate(starts):
        block = lines[i+1:starts[n+1] if n+1 < len(starts) else min(len(lines), i+40)]
        day = _future_date(lines[i])
        if not day or not any('Kassam' in line for line in block):
            continue
        team_lines = [line for line in block if re.search(r'\b(?:FC|United|City|Town|Rovers|Wanderers|Athletic|Albion|County|Dons)\b', line, re.I)]
        if not team_lines or not team_lines[0].lower().startswith('oxford united'):
            continue
        opponent = next((line for line in team_lines[1:] if not line.lower().startswith('oxford united')), None)
        if not opponent:
            continue
        opponent = re.split(r'(?=\b(?:FC|United|City|Town|Rovers|Wanderers|Athletic|Albion|County|Dons)\b)', opponent)[0].strip() or opponent
        time_line = next((line for line in block if 'Kick off' in line), '')
        time_match = re.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm))', time_line, re.I)
        start = day
        if time_match:
            tm = dateparser.parse(time_match.group(1)).strftime('%H:%M')
            start += 'T' + tm
        event = _base(f'Oxford United v {opponent}', start, 'Kassam Stadium', url, 'home match', 'Home fixture; kick-off can change')
        results.append(event)
    return results


def ceremonies(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for li in soup.find_all('li'):
        line = li.get_text(' ', strip=True)
        match = re.match(r'^(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+\d{1,2}\s+[A-Za-z]+\s+20\d{2}', line)
        if not match or 'in absence only' in line.lower():
            continue
        day = _future_date(match.group(0))
        if not day:
            continue
        event = _base('Oxford degree ceremonies', day, 'Sheldonian Theatre', url, 'graduation', 'In-person ceremony; individual colleges attend on selected dates')
        results.append(event)
    return results


def terms(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for heading in soup.find_all('h2'):
        name = heading.get_text(' ', strip=True).lower()
        if not (name.startswith('dates of full term') or name == 'dates of term'):
            continue
        table = heading.find_next('table')
        if not table:
            continue
        for tr in table.find_all('tr'):
            cells = [c.get_text(' ', strip=True) for c in tr.find_all(['th', 'td'])]
            term = next((c for c in cells if re.search(r'\b(?:Michaelmas|Hilary|Trinity) 20\d{2}\b', c)), None)
            if not term:
                continue
            pos = cells.index(term)
            if len(cells) < pos + 3:
                continue
            year = int(re.search(r'20\d{2}', term).group())
            mode = 'full term' if 'full' in name else 'term'
            for label, raw in [('starts', cells[pos+1]), ('ends', cells[pos+2])]:
                day = _future_date(raw + ' ' + str(year))
                if day:
                    results.append(_base(f'Oxford {term} {mode} {label}', day, 'Oxford city centre', url, 'term date', 'Background student-population signal'))
    return results


def theatre(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    for heading in soup.find_all('h2'):
        title = heading.get_text(' ', strip=True)
        if not title or len(title) > 180:
            continue
        segment = []
        for sibling in heading.next_siblings:
            if getattr(sibling, 'name', None) == 'h2':
                break
            segment.append(sibling.get_text(' ', strip=True) if hasattr(sibling, 'get_text') else str(sibling).strip())
            if len(segment) > 20:
                break
        text = ' '.join(segment)
        match = re.search(r'\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+\d{1,2}\s+[A-Za-z]{3}\s+20\d{2}\b', text)
        if not match:
            continue
        day = _future_date(match.group())
        if not day:
            continue
        link = heading.find('a', href=True)
        results.append(_base(title, day, 'New Theatre Oxford', urljoin(url, link['href']) if link else url, 'performance', 'Show date; check performance time'))
    return results


def access(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    results = []
    seen = set()
    for link in soup.find_all('a', href=True):
        title = link.get_text(' ', strip=True)
        if not re.search(r'\bOxford\b|Broad Street|Cornmarket|St Giles', title, re.I):
            continue
        match = re.search(r'\b\d{1,2}\s+[A-Za-z]+\s+20\d{2}\b', title)
        if not match:
            continue
        day = _future_date(match.group())
        if not day or (title, day) in seen:
            continue
        seen.add((title, day))
        results.append(_base(title, day, 'Oxford roads', urljoin(url, link['href']), 'access alert', 'Check official road and footpath restrictions'))
    return results


ADAPTERS = {'fixtures': fixtures, 'ceremonies': ceremonies, 'terms': terms, 'theatre': theatre, 'access': access}
