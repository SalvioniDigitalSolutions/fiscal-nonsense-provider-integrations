#!/usr/bin/env python3
"""Exact public Swiss mortgage rate adapters. Python 3.10+, standard library only."""
import argparse
import concurrent.futures
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import urllib.request
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
USER_AGENT = 'FiscalNonsense-PublicRates/0.1 (+https://github.com/SalvioniDigitalSolutions/fiscal-nonsense-provider-integrations)'
MAX_BYTES = 4 * 1024 * 1024
MAX_AGE = timedelta(hours=24)

class SourceChanged(ValueError):
    pass

class PageText(HTMLParser):
    """Preserve visible table-cell boundaries; ignore script, style, SVG and noscript containers."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip += 1
        if tag in ('tr', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'li', 'br'):
            self.parts.append('\n')
        if tag in ('td', 'th'):
            self.parts.append(' | ')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'svg'):
            self.skip = max(0, self.skip - 1)
        if tag in ('tr', 'p', 'div', 'h1', 'h2', 'h3', 'h4', 'li'):
            self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
    def text(self):
        return '\n'.join(' '.join(line.split()) for line in ''.join(self.parts).splitlines() if line.strip())

def providers():
    return json.loads((ROOT / 'providers.json').read_text())

def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

def field(pattern, text):
    match = re.search(pattern, text)
    if not match:
        raise SourceChanged('Required source date/marker disappeared')
    return match.group(1).strip()

def extract(provider, html, fetched_at=None):
    fetched_at = fetched_at or datetime.now(timezone.utc)
    parser = PageText()
    parser.feed(html)
    text = parser.text()
    source_date = field(provider['datePattern'], text) if provider.get('datePattern') else None
    valid_until = field(provider['validUntilPattern'], text) if provider.get('validUntilPattern') else None
    expires = fetched_at + MAX_AGE
    if valid_until:
        # Date-only publication expiry: conservative UTC start, no invented intraday validity.
        expiry = datetime.strptime(valid_until, '%d.%m.%Y').replace(tzinfo=timezone.utc)
        if fetched_at >= expiry:
            raise SourceChanged('Published rate validity has ended')
        expires = min(expires, expiry)
    rates = []
    for section in provider['sections']:
        starts = list(re.finditer(section['start'], text))
        if len(starts) != 1:
            raise SourceChanged('Missing or ambiguous product section')
        tail = text[starts[0].end():]
        end = re.search(section['end'], tail)
        if not end:
            raise SourceChanged('Missing product section end')
        block = tail[:end.start()]
        if section.get('headerPattern') and not re.search(section['headerPattern'], block):
            raise SourceChanged('Rate column headings changed')
        matches = list(re.finditer(section['pattern'], block))
        terms = [int(m['term']) for m in matches]
        if sorted(terms) != sorted(section['terms']):
            raise SourceChanged('Unexpected terms, duplicate rows or incomplete rate table')
        for match in matches:
            raw_rate = match['rate']
            rate = raw_rate.replace(',', '.')
            if not Decimal('0') <= Decimal(rate) <= Decimal('20'):
                raise SourceChanged('Rate outside sanity range; manual review required')
            rates.append({
                'id': f"{provider['id']}:{section['id']}:{match['term']}",
                'providerId': provider['id'], 'providerName': provider['name'],
                'lenderGroup': provider.get('lenderGroup'),
                'country': provider['country'], 'currency': provider['currency'],
                'product': section['label'], 'rateType': 'fixed',
                'termYears': int(match['term']), 'annualRatePercent': rate,
                'publishedRateText': raw_rate, 'qualifier': section.get('qualifier', 'published'),
                'binding': False, 'personalised': False, 'derived': False,
                'conditions': section.get('conditions', provider['conditions']),
                'conditionsReviewedOn': '2026-09-22',
                'conditionsComplete': False,
                'conditionsUrl': provider.get('conditionsUrl', provider['url']),
                'sourceUrl': provider['url'], 'sourcePublishedDateText': source_date,
                'sourceValidUntilDateText': valid_until,
                'retrievedAt': iso(fetched_at), 'expiresAt': iso(expires),
                'sourceSha256': sha256(html.encode()).hexdigest(),
                'sourceEvidence': match.group(0),
            })
    return rates

class SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme != 'https' or urlparse(newurl).hostname != urlparse(req.full_url).hostname:
            raise SourceChanged('Unexpected redirect host or protocol')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def fetch(provider):
    request = urllib.request.Request(provider['url'], headers={'User-Agent': USER_AGENT, 'Cache-Control': 'no-cache'})
    with urllib.request.build_opener(SameHostRedirect).open(request, timeout=25) as response:
        if 'text/html' not in response.headers.get('Content-Type', ''):
            raise SourceChanged('Expected an HTML rate page')
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise SourceChanged('Response exceeds size limit')
        html = body.decode(response.headers.get_content_charset() or 'utf-8')
    return extract(provider, html)

def available_rates(document, now=None, term=None):
    """Consumer-side freshness gate: expired snapshots must not remain current."""
    now = now or datetime.now(timezone.utc)
    return [rate for rate in document['rates']
            if datetime.fromisoformat(rate['retrievedAt'].replace('Z', '+00:00')) <= now
            < datetime.fromisoformat(rate['expiresAt'].replace('Z', '+00:00'))
            and (term is None or rate['termYears'] == term)]

def collect(selected, loader=fetch):
    def run(provider):
        try:
            rates = loader(provider)
            return rates, {'providerId': provider['id'], 'status': 'ok', 'rateCount': len(rates)}
        except Exception as error:
            return [], {'providerId': provider['id'], 'status': 'unavailable', 'rateCount': 0,
                        'reason': f'{type(error).__name__}: {error}'}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run, selected))
    return {'schemaVersion': 'public-mortgage-rates/1', 'generatedAt': iso(datetime.now(timezone.utc)),
            'disclosure': 'Exact lender-published rates, not personalised or binding quotes. Conditions and source labels apply. Retrieval time is not the lender publication date.',
            'providers': [status for _, status in results],
            'rates': [rate for rates, _ in results for rate in rates]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', action='append', help='Provider ID; repeat to select several. Default: all.')
    parser.add_argument('--term', type=int, help='Only return an explicitly published fixed term; no interpolation.')
    parser.add_argument('--output', type=Path, help='Write JSON atomically (default: stdout).')
    args = parser.parse_args()
    selected = providers()
    if args.provider:
        unknown = set(args.provider) - {p['id'] for p in selected}
        if unknown:
            parser.error('Unknown provider: ' + ', '.join(sorted(unknown)))
        selected = [p for p in selected if p['id'] in args.provider]
    result = collect(selected)
    result['rates'] = available_rates(result, term=args.term)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        temporary = args.output.with_suffix(args.output.suffix + '.tmp')
        temporary.write_text(serialized)
        temporary.replace(args.output)
    else:
        print(serialized, end='')
    return 2 if any(p['status'] != 'ok' for p in result['providers']) else 0

if __name__ == '__main__':
    sys.exit(main())
