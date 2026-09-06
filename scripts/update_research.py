"""Collect public institution sources; never invent dates or bypass login walls."""
import concurrent.futures
import datetime as dt
import email.utils
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data/research.json'
SOURCES = {
    'bofa': 'https://bofaglobalresearch.podbean.com/feed.xml',
    'jefferies': 'https://www.jefferies.com/feed/',
    'ms': 'https://www.morganstanley.com/insights/podcasts/thoughts-on-the-market',
    'jpm': 'https://marketmatters.podbean.com/feed.xml',
    'evercore': 'https://www.evercore.com/our-business-and-capabilities/equities/',
}

def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; ResearchRadar/1.0)'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()

def plain(value):
    return ' '.join(BeautifulSoup(value or '', 'html.parser').get_text(' ', strip=True).split())

def date(value):
    value = value.strip()
    for fmt in ('%Y-%m-%d', '%B %d, %Y', '%b %d, %Y'):
        try:
            return dt.datetime.strptime(value[:10] if fmt == '%Y-%m-%d' else value, fmt).date().isoformat()
        except ValueError:
            pass
    return email.utils.parsedate_to_datetime(value).date().isoformat()

def report(org, title, published, url, summary='', kind='官方摘要'):
    if urlsplit(url).scheme != 'https' or urlsplit(url).hostname != urlsplit(SOURCES[org]).hostname:
        raise ValueError('Non-official article URL')
    title, summary = plain(title), plain(summary)
    if not title:
        raise ValueError('Missing title')
    topic = '行业研究'
    for label, pattern in [('科技AI', r'\bAI\b|software|technology|data center'), ('能源', r'\boil\b|energy|gas'), ('宏观经济', r'inflation|rates|payroll|fed\b|economy'), ('市场策略', r'equit|stocks|market|invest'), ('消费', r'consumer|spending')]:
        if re.search(pattern, title, re.I):
            topic = label
            break
    return dict(org=org, title=title, date=date(published), dateText=date(published), url=url,
                summary=summary[:650] or '机构未提供公开摘要，请打开原文查看。', type=kind, topic=topic,
                tags=['官方原文', '自动采集'], source='机构公开', access='公开访问')

def collect(org):
    body = fetch(SOURCES[org])
    rows = []
    if org in ('bofa', 'jefferies', 'jpm'):
        for item in ET.fromstring(body).findall('.//item'):
            url = item.findtext('link', '')
            if org == 'jefferies' and '/insights/' not in url:
                continue
            rows.append(report(org, item.findtext('title'), item.findtext('pubDate'), url,
                               item.findtext('description'), '播客' if org in ('bofa', 'jpm') else '官方摘要'))
    elif org == 'ms':
        soup = BeautifulSoup(body, 'html.parser')
        for box in soup.select('.episode-details'):
            a, stamp = box.select_one('.episode-title a'), box.select_one('.episode-eyebrow')
            if not a or not stamp:
                continue
            description = box.parent.select_one('.episode-description')
            rows.append(report(org, a.get_text(), stamp.get_text(), urljoin(SOURCES[org], a['href']),
                               description.get_text() if description else '', '播客'))
    else:
        soup = BeautifulSoup(body, 'html.parser')
        # Only dated article metadata is eligible, never a landing page's modified date.
        links = list(dict.fromkeys(urljoin(SOURCES[org], a['href']) for a in soup.select('a[href]')
                    if '/insights/global-research/' in a['href'] or '/insights/research/' in a['href']))[:20]
        for url in links:
            page = BeautifulSoup(fetch(url), 'html.parser')
            published = page.select_one('meta[property="article:published_time"], meta[name="date"]')
            title = page.select_one('h1')
            summary = page.select_one('meta[name="description"]')
            if published and title:
                rows.append(report(org, title.get_text(), published['content'], url, summary['content'] if summary else ''))
    if not rows:
        raise ValueError('未找到可核验发布日期的公开条目，保留已有资料')
    return list({r['url']: r for r in rows}.values())

def main():
    previous = json.loads(OUTPUT.read_text(encoding='utf-8')) if OUTPUT.exists() else {'reports': [], 'sources': {}}
    now = dt.datetime.now(dt.timezone.utc)
    stamp = now.isoformat()
    merged = {r['url']: r for r in previous['reports']}
    statuses = {}
    succeeded = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        jobs = {pool.submit(collect, org): org for org in SOURCES}
        for job in concurrent.futures.as_completed(jobs):
            org = jobs[job]
            old = previous.get('sources', {}).get(org, {})
            try:
                rows = job.result()
                merged.update({r['url']: r for r in rows})
                statuses[org] = dict(status='ok', checkedAt=stamp, lastSuccessAt=stamp, count=len(rows), url=SOURCES[org])
                succeeded += 1
            except Exception as exc:
                statuses[org] = dict(status='error', checkedAt=stamp, lastSuccessAt=old.get('lastSuccessAt'), message=str(exc)[:180], url=SOURCES[org])
            print(org, statuses[org])
    # Retain a year server-side; the UI applies a rolling six-calendar-month window.
    cutoff = (now.date() - dt.timedelta(days=366)).isoformat()
    rows = sorted((r for r in merged.values() if cutoff <= r['date'] <= now.date().isoformat()), key=lambda r: r['date'], reverse=True)
    payload = dict(schemaVersion=1, checkedAt=stamp, lastSuccessAt=stamp if succeeded else previous.get('lastSuccessAt'), sources=statuses, reports=rows)
    OUTPUT.parent.mkdir(exist_ok=True)
    temporary = OUTPUT.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(OUTPUT)
    return 0 if succeeded else 1

if __name__ == '__main__':
    sys.exit(main())
