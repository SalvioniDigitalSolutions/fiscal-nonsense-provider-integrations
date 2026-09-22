#!/usr/bin/env python3
"""Official Swiss consumer-credit published rates; Python standard library only."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import math
import os
import tempfile
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent
PERCENT = r'(\d{1,2}(?:[.,]\d{1,3})?)\s*%'

class SourceChanged(ValueError):
    pass

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def text_from_html(html):
    p = TextParser()
    p.feed(html)
    return ' '.join(' '.join(p.parts).split())

def providers():
    return json.loads((BASE / 'providers.json').read_text())

def decimal(value):
    # Preserve source precision; no numerical transformations or price arithmetic.
    return value.replace(',', '.')

def parse(provider, html, observed_at, source_hash=None):
    text = text_from_html(html)
    pattern = provider['range_anchor'] + r'\s*' + PERCENT + r'\s+und\s+' + PERCENT
    matches = list(re.finditer(pattern, text, re.I))
    pairs = {(decimal(m[1]), decimal(m[2])) for m in matches}
    if len(pairs) != 1:
        raise SourceChanged('Missing or conflicting effective annual interest range')
    lower, upper = next(iter(pairs))
    if not 0 <= float(lower) <= float(upper) <= 100:
        raise SourceChanged('Invalid interest range')
    common = {
        'provider_id': provider['id'], 'provider_name': provider['name'],
        'lender_group': provider['lender_group'], 'country': 'CH', 'currency': 'CHF',
        'category': 'personal-loan', 'product': provider['product'],
        'rate_unit': 'percent-per-year', 'rate_basis': 'effective-annual-interest',
        'binding_quote': False, 'personalized': False, 'derived': False,
        'source_url': provider['url'], 'observed_at': observed_at,
        'provider_effective_date': None, 'freshness_ttl_hours': 24,
        'source_sha256': source_hash or hashlib.sha256(html.encode()).hexdigest(),
        'conditions': provider['conditions'],
    }
    rows = [{**common, 'id': provider['id'] + ':published-range',
             'rate_kind': 'published-range', 'rate_min_percent': lower,
             'rate_max_percent': upper, 'source_excerpt': matches[0][0]}]
    if provider['id'] == 'cashgate':
        # Parse the labelled desktop matrix, requiring all cohort and term labels.
        # Do not infer which unlisted term or residence combination qualifies.
        anchor = r'Laufzeit in Monaten/ Zinssatz ≤ 48 60 ≥ 72 ab CHF 4[’\']500 Schweizer Pass C-Bewilligung Mit Wohneigentum '
        triplet = PERCENT + r'\s+' + PERCENT + r'\s+' + PERCENT
        grid = re.search(anchor + triplet + r' Ohne Wohneigentum ' + triplet +
                         r" unter CHF 4[’']500 Schweizer Pass C-Bewilligung B-Bewilligung - " + triplet, text)
        if grid is None:
            raise SourceChanged('Cashgate cohort table changed; refusing partial extraction')
        cohorts = [
            {'monthly_income_chf': '>=4500', 'residency': ['Swiss citizen', 'C permit'], 'homeownership': True},
            {'monthly_income_chf': '>=4500', 'residency': ['Swiss citizen', 'C permit'], 'homeownership': False},
            {'monthly_income_chf': '<4500', 'residency': ['Swiss citizen', 'C permit', 'B permit'], 'homeownership': 'not specified'},
        ]
        for i, value in enumerate(grid.groups()):
            if not float(lower) <= float(decimal(value)) <= float(upper):
                raise SourceChanged('Cohort rate outside published overall range')
            rows.append({**common, 'id': f'cashgate:cohort-{i//3+1}:term-{i%3+1}',
                'rate_kind': 'published-conditional', 'rate_basis': 'published-interest-rate',
                'rate_percent': decimal(value), 'eligibility_cohort': {**cohorts[i//3], 'income_basis': 'not specified by source'},
                'term_months_source_label': ['≤ 48', '60', '≥ 72'][i%3],
                'product_term_months_range': [12, 84],
                'source_excerpt': f"{['≤ 48', '60', '≥ 72'][i%3]} months: {value}%"})
    return rows

def fetch(provider, timeout=30):
    request = urllib.request.Request(provider['url'], headers={
        'User-Agent': 'FiscalNonsensePublicRates/0.1 (public pricing research)',
        'Accept': 'text/html', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if response.status != 200 or 'text/html' not in response.headers.get('Content-Type', ''):
            raise SourceChanged('Expected HTTP 200 HTML')
        if urlparse(response.url).hostname != urlparse(provider['url']).hostname:
            raise SourceChanged('Unexpected cross-domain redirect')
        raw = response.read(5_000_001)
        if len(raw) > 5_000_000: raise SourceChanged('Source exceeds maximum size')
        html = raw.decode(response.headers.get_content_charset() or 'utf-8')
    now = datetime.now(timezone.utc).isoformat()
    return parse(provider, html, now, hashlib.sha256(raw).hexdigest())

def collect(selected=None):
    results = []
    errors = []
    for provider in providers():
        if selected and provider['id'] not in selected: continue
        try: results.extend(fetch(provider))
        except Exception as exc:
            errors.append({'provider_id': provider['id'], 'status': 'unavailable',
                           'error': str(exc), 'source_url': provider['url']})
    return {'schema_version': '1.0', 'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'ok' if not errors else 'partial' if results else 'unavailable',
            'rates': results, 'errors': errors}

def available_rates(document, now):
    """Return only fresh observations, never future-dated or older than 24h.

    `now` is an aware datetime or ISO timestamp. Malformed records fail closed;
    malformed `now` raises ValueError. A record TTL can shorten, never extend, 24h.
    """
    def timestamp(value):
        result = datetime.fromisoformat(value.replace('Z', '+00:00')) if isinstance(value, str) else value
        if not isinstance(result, datetime) or result.tzinfo is None or result.utcoffset() is None:
            raise ValueError('Timezone-aware datetime required')
        return result
    current = timestamp(now)
    if not isinstance(document, dict) or document.get('status') not in ('ok', 'partial'):
        return []
    failed = {error.get('provider_id') for error in document.get('errors', []) if isinstance(error, dict)}
    result = []
    for row in document.get('rates', []):
        try:
            if not isinstance(row, dict) or row.get('provider_id') in failed:
                continue
            age = (current - timestamp(row['observed_at'])).total_seconds()
            ttl = float(row['freshness_ttl_hours'])
            if not math.isfinite(ttl) or ttl <= 0:
                continue
            if 0 <= age <= min(ttl, 24) * 3600:
                result.append(row)
        except (ValueError, TypeError, KeyError, OverflowError):
            continue
    return result

def atomic_write(path, content):
    """Replace an output only after a complete same-directory write and fsync."""
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.' + path.name + '.', suffix='.tmp', delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', action='append', choices=[p['id'] for p in providers()])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = collect(args.provider)
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output: atomic_write(args.output, output)
    else: print(output, end='')
    return 1 if result['errors'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
