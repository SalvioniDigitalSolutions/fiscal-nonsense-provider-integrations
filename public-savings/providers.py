#!/usr/bin/env python3
"""Exact public Swiss cash-rate schedules. Python standard library; no quote math."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import html
import json
import os
import tempfile
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# start and end markers must surround the product's published rate block.
# Multiple percentages remain a schedule, never converted to a personal quote.
def spec(product, category, start, end, count, currency='CHF'):
    return dict(product=product, category=category, start=start, end=end, count=count, currency=currency)

SOURCES = {
 'hbl': dict(name='Hypothekarbank Lenzburg', url='https://www.hbl.ch/de/zinssaetze-konditionen', products=[
  spec('Sparkonto','savings',r'Sparen & Vorsorgen Sparkonto ',r' Sparkonto Extra',1),
  spec('Sparkonto Extra','savings',r'Sparkonto Extra ',r' Aktionärssparkonto',2),
  spec('Aktionärssparkonto','savings',r'Aktionärssparkonto ',r' Jugend-Sparkonto',2),
  spec('Jugend-Sparkonto','savings',r'Jugend-Sparkonto ',r' Mietkautionssparkonto',2),
  spec('Mietkautionssparkonto','rental_deposit',r'Mietkautionssparkonto ',r' Vorsorgekonto 3a',1),
  spec('Vorsorgekonto 3a','pillar_3a_cash',r'Vorsorgekonto 3a ',r' Freizügigkeitskonto 2. Säule',1),
  spec('Freizügigkeitskonto 2. Säule','vested_benefits_cash',r'Freizügigkeitskonto 2\. Säule ',r' Aare-Strategien',1)]),
 'zkb': dict(name='Zürcher Kantonalbank',url='https://www.zkb.ch/de/private/zinsen-preise.html',products=[
  spec('ZKB Sparkonto','savings',r'Konten zum Sparen ZKB Sparkonto ',r' ZKB Umweltsparkonto',2),
  spec('ZKB Umweltsparkonto','savings',r'ZKB Umweltsparkonto Zinssatz ',r' ZKB Sparkonto Young',1),
  spec('ZKB Sparkonto Young','savings',r'ZKB Sparkonto Young Sparkapital ',r' ZKB Geschenksparkonto',2),
  spec('ZKB Geschenksparkonto','savings',r'ZKB Geschenksparkonto Sparkapital ',r' ZKB Mieterkautionssparkonto',2),
  spec('ZKB Mieterkautionssparkonto','rental_deposit',r'ZKB Mieterkautionssparkonto Zinssatz ',r' Konten zum Vorsorgen',1),
  spec('ZKB Säule-3a Konto','pillar_3a_cash',r'ZKB Säule-3a Konto Zinssatz ',r' ZKB Freizügigkeitskonto',1),
  spec('ZKB Freizügigkeitskonto','vested_benefits_cash',r'ZKB Freizügigkeitskonto Zinssatz ',r' Hypothekarzinsen',1)]),
 'bsu': dict(name='Bank BSU',url='https://www.bankbsu.ch/zinssaetze',products=[
  spec('Sparkonto','savings',r'(?<!Young )Sparkonto (?=\d)',r' Verrechnungssteuer',2),
  spec('BSU Young Sparkonto','savings',r'BSU Young Sparkonto (?=\d)',r' Verrechnungssteuer',3),
  spec('Geschenksparkonto','savings',r'Geschenksparkonto (?=\d)',r' Verrechnungssteuer',2),
  spec('Anlagesparkonto','savings',r'Anlagesparkonto (?=\d)',r' Verrechnungssteuer',3),
  spec('Mietkautionssparkonto','rental_deposit',r'Mietkautionssparkonto (?=\d)',r' Verrechnungssteuer',1),
  spec('PRIVOR Vorsorgekonto 3. Säule','pillar_3a_cash',r'PRIVOR Vorsorgekonto 3\. Säule (?=\d)',r' PRIVOR Freizügigkeitskonto',1),
  spec('PRIVOR Freizügigkeitskonto','vested_benefits_cash',r'PRIVOR Freizügigkeitskonto (?=\d)',r' Firmenkunden Zahlen',1)]),
 'valiant': dict(name='Valiant',url='https://www.valiant.ch/de/privatkunden/zahlen-zinssatz-barometer',products=[
  spec('Geschenkkonto','savings',r'Geschenkkonto Zinssatz ',r' Lila Sparkonto',2),
  spec('Mietkautionskonto','rental_deposit',r'Mietkautionskonto Zinssatz ',r' Sparkonto Zinssatz',1),
  spec('Sparkonto CHF','savings',r'Sparkonto Zinssatz CHF: ',r' Zinssatz EUR:',2),
  spec('Sparkonto EUR','savings',r'Zinssatz EUR: ',r' Zinssatz USD:',2,'EUR'),
  spec('Sparkonto USD','savings',r'Zinssatz USD: ',r' Young Plus Sparkonto',2,'USD'),
  spec('Young Plus Sparkonto','savings',r'Young Plus Sparkonto Zinssatz ',r' Letzte Zinssatzänderung:',2),
  spec('Freizügigkeitskonto 2. Säule','vested_benefits_cash',r'Freizügigkeitskonto 2\. Säule Zinssatz ',r' PRIVOR Vorsorgekonto',1),
  spec('PRIVOR Vorsorgekonto 3a','pillar_3a_cash',r'PRIVOR Vorsorgekonto 3a Zinssatz ',r' (?:PRIVOR Vorsorgekonto|Letzte Zinssatzänderung)',1)]),
 'cler': dict(name='Bank Cler',url='https://www.cler.ch/de/info/zinssatze-fur-privatkunden',products=[
  spec('Sparkonto','savings',r'Sparkonto (?=\d)',r' Sparkonto Jugend',2),
  spec('Sparkonto Jugend / Geschenksparkonto','savings',r'Sparkonto Jugend / Geschenksparkonto ',r' Sparkonto Plus',2),
  spec('Sparkonto Euro','savings',r'Sparkonto Euro (?=\d)',r' Sparkonto Zak',1,'EUR'),
  spec('Vorsorgekonto 3','pillar_3a_cash',r'Vorsorgekonto 3 \(Säule 3a\) ',r' Vorsorgekonto Zak',2),
  spec('Vorsorgekonto Zak','pillar_3a_cash',r'Vorsorgekonto Zak (?=\d)',r' Freizügigkeitskonto',1),
  spec('Freizügigkeitskonto','vested_benefits_cash',r'Freizügigkeitskonto \(2\. Säule\) ',r' Mehr über Vorsorgen',1)])
}

RATE = re.compile(r'\d+[.,]\s*\d(?:\s*\d)*\s*%')

def plain_text(raw):
    raw=re.sub(r'<(script|style|noscript)\b[^>]*>.*?</\1>', '', raw, flags=re.S|re.I)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', raw))).strip()

def parse(provider_id, raw, fetched_at=None):
    source=SOURCES[provider_id]; text=plain_text(raw)
    if provider_id=='hbl':
        marker='Sparen & Vorsorgen Sparkonto '
        if marker not in text: raise ValueError('Savings section missing')
        text=text[text.index(marker):]
    fetched_at=fetched_at or dt.datetime.now(dt.timezone.utc).isoformat()
    dates=[]
    if provider_id in ('bsu','valiant'):
        dates=list(dict.fromkeys(re.findall(r'(?:Stand|Letzte Zinssatzänderung:)\s*(\d{1,2}\. [A-Za-zäöüÄÖÜ]+ \d{4})',text)))
    conditions=[]
    if provider_id=='cler':
        m=re.search(r'Je nach Bankpaket für Privatkunden.*?(?=Finanzwissen:)',text)
        if not m: raise ValueError('Cler package and threshold footnotes missing')
        conditions.append(m.group(0).strip())
    products=[]
    for p in source['products']:
        matches=list(re.finditer(p['start']+'(.{1,1000}?)'+p['end'],text))
        if not matches: raise ValueError('Missing product block: '+p['product'])
        blocks={m.group(1).strip() for m in matches}
        if len(blocks)!=1: raise ValueError('Ambiguous repeated product: '+p['product'])
        block=blocks.pop(); rate_matches=list(RATE.finditer(block))
        if len(rate_matches)!=p['count']: raise ValueError('Unexpected rate count: '+p['product'])
        rates=[]
        for m in rate_matches:
            value=re.sub(r'\s+','',m.group(0)).rstrip('%').replace(',','.')
            if not 0<=float(value)<=20: raise ValueError('Out-of-range interest rate')
            rates.append({'percent':value,'published_text':m.group(0),'offset_in_evidence':m.start()})
        products.append({'provider_id':provider_id,'provider_name':source['name'], 'product':p['product'],
          'country':'CH','currency':p['currency'],'category':p['category'],
          'value_type':'published_interest_rate_schedule','unit':'percent_per_annum',
          'published_rates':rates,'evidence_text':block,'source_url':source['url'],
          'provider_conditions':conditions,'fetched_at':fetched_at,
          'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),
          'personalized_quote':False,'derived':False})
    if provider_id=='zkb':
        dates=list(dict.fromkeys(d for p in products for d in re.findall(r'Letzte Änderung: (\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2})',p['evidence_text'])))
    return {'provider_id':provider_id,'source_url':source['url'],'fetched_at':fetched_at,
      'status':'ok','published_date_labels':dates,'products':products}

def fetch(provider_id):
    source=SOURCES[provider_id]
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    try:
        request=urllib.request.Request(source['url'],headers={'User-Agent':'FiscalNonsense-PublicRates/1.0 (+https://fiscalnonsense.com)','Cache-Control':'no-cache'})
        with urllib.request.urlopen(request,timeout=30) as response:
            if response.status!=200: raise ValueError('Unexpected HTTP status')
            if 'text/html' not in response.headers.get('Content-Type',''): raise ValueError('Expected HTML')
            final_url=urllib.parse.urlparse(response.geturl())
            original_url=urllib.parse.urlparse(source['url'])
            if final_url.scheme!='https' or final_url.hostname!=original_url.hostname:
                raise ValueError('Unexpected final source host or scheme')
            payload=response.read(4000001)
            if len(payload)>4000000: raise ValueError('Source response exceeds size limit')
            raw=payload.decode('utf-8')
        return parse(provider_id,raw,now)
    except Exception as exc:
        return {'provider_id':provider_id,'source_url':source['url'],'fetched_at':now,'status':'error','error':str(exc),'products':[]}

def is_fresh(record, now=None, max_age_hours=24):
    """Require an aware retrieval timestamp no later than now and <=24h old."""
    now=now or dt.datetime.now(dt.timezone.utc)
    try:
        fetched=dt.datetime.fromisoformat(record['fetched_at'].replace('Z','+00:00'))
        if fetched.tzinfo is None or now.tzinfo is None or max_age_hours < 0:
            return False
        age=(now-fetched).total_seconds()
        return record.get('status','ok')=='ok' and 0 <= age <= max_age_hours*3600
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def atomic_write(path, rendered):
    """Replace only after a complete UTF-8 JSON write in the target directory."""
    path=Path(path)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,
                                         prefix='.'+path.name+'.',delete=False) as handle:
            temporary=handle.name
            handle.write(rendered)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary,path)
    finally:
        if temporary and os.path.exists(temporary): os.unlink(temporary)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider',choices=list(SOURCES),action='append')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(fetch,args.provider or SOURCES))
    output={'schema_version':1,'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),
      'freshness_policy':'Fresh public HTTP retrieval on each run; no cached fallback. A successful fetch is not a rate guarantee. Treat saved data older than 24 hours as stale.',
      'providers':results}
    rendered=json.dumps(output,ensure_ascii=False,indent=2)+'\n'
    if args.output: atomic_write(args.output,rendered)
    else: print(rendered,end='')
    return 1 if any(r['status']!='ok' for r in results) else 0

if __name__=='__main__':sys.exit(main())
