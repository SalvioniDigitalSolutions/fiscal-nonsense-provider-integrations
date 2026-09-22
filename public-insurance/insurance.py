#!/usr/bin/env python3
"""BAG Swiss basic-health published tariffs. Python 3.10+, standard library.
No premium calculation: amounts are exact source strings; filters select rows.
"""
import argparse
import base64
import csv
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parent
LANDING = 'https://opendata.swiss/de/dataset/health-insurance-premiums'
MAX_BYTES = 80 * 1024 * 1024
MAX_AGE = timedelta(days=1)
CANTONS = set('AG AI AR BE BL BS FR GE GL GR JU LU NE NW OW SG SH SO SZ TG TI UR VD VS ZG ZH'.split())
HEADERS = ['Versicherer','Kanton','Hoheitsgebiet','Geschäftsjahr','Erhebungsjahr','Region','Altersklasse','Unfalleinschluss','Tarif','Tariftyp','Altersuntergruppe','Franchisestufe','Franchise','Prämie','isBaseP','isBaseF','Tarifbezeichnung']

class SourceChanged(ValueError):
    pass

def iso(now):
    return now.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

def source_url(year):
    # Public BAG download path, deterministic year-specific official archive.
    path = base64.b64encode(f'/Praemien/Archiv_Praemien_{year}.zip'.encode()).decode()
    return 'https://opendata.bagnet.ch/?r=/download&path=' + quote(path, safe='')

def download(url):
    with urlopen(Request(url, headers={'User-Agent':'FiscalNonsense-PublicInsurance/0.1'}), timeout=60) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise SourceChanged('Source exceeds download size limit')
        return data

def csv_rows(data, delimiter=','):
    reader = csv.DictReader(io.StringIO(data.decode('utf-8-sig')), delimiter=delimiter)
    return reader

def archive_files(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        wanted = ['Prämien_CH.csv', 'Tarife.csv', 'Einzugsgebiete.csv', 'Eingeschr.-Tät.gebiete.csv']
        result = {}
        for name in wanted:
            matches = [n for n in archive.namelist() if n.split('/')[-1] == name]
            if len(matches) != 1:
                raise SourceChanged(f'Missing or ambiguous archive member: {name}')
            if archive.getinfo(matches[0]).file_size > MAX_BYTES:
                raise SourceChanged('Uncompressed archive member exceeds limit')
            result[name] = archive.read(matches[0])
        return result

def normalize(row, year):
    if set(row) != set(HEADERS) or None in row.values():
        raise SourceChanged('Unexpected premium columns')
    if row['Geschäftsjahr'] != str(year) or row['Hoheitsgebiet'] != 'CH':
        raise SourceChanged('Wrong coverage year or territory')
    try:
        amount = Decimal(row['Prämie'])
    except InvalidOperation as exc:
        raise SourceChanged('Invalid premium') from exc
    if not amount.is_finite() or not 0 <= amount <= 10000:
        raise SourceChanged('Invalid premium range')
    if row['Altersklasse'] not in ('AKL-KIN','AKL-JUG','AKL-ERW') or row['Unfalleinschluss'] not in ('MIT-UNF','OHN-UNF'):
        raise SourceChanged('Unknown eligibility code')
    return {
        'insurer':str(int(row['Versicherer'])), 'canton':row['Kanton'],
        'region':row['Region'], 'age':row['Altersklasse'],
        'accident':row['Unfalleinschluss'], 'tariff':row['Tarif'],
        'subgroup':row['Altersuntergruppe'], 'deductible':row['Franchise'],
        'premium':row['Prämie'], 'raw':json.dumps(row, ensure_ascii=False)
    }

def import_archive(data, destination, year, fetched_at=None, network_verified=False):
    """Validate entire archive and atomically replace local SQLite catalogue."""
    now = fetched_at or datetime.now(timezone.utc)
    files = archive_files(data)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + '.building')
    temp.unlink(missing_ok=True)
    db = sqlite3.connect(temp)
    try:
        db.execute('CREATE TABLE premiums (insurer TEXT,canton TEXT,region TEXT,age TEXT,accident TEXT,tariff TEXT,subgroup TEXT,deductible TEXT,premium TEXT,raw TEXT)')
        db.execute('CREATE TABLE metadata (data TEXT)')
        db.execute('CREATE TABLE conditions (kind TEXT,insurer TEXT,raw TEXT)')
        reader = csv_rows(files['Prämien_CH.csv'])
        if reader.fieldnames != HEADERS:
            raise SourceChanged('Premium CSV schema changed')
        count = 0
        insurers = set()
        cantons = set()
        for row in reader:
            norm = normalize(row, year)
            # ZE/ZR are special territories; never present as ordinary cantons.
            db.execute('INSERT INTO premiums VALUES (?,?,?,?,?,?,?,?,?,?)',tuple(norm.values()))
            count += 1
            insurers.add(norm['insurer'])
            cantons.add(norm['canton'])
        if not count:
            raise SourceChanged('Empty premium source; refusing to replace catalogue')
        for name in ('Tarife.csv','Einzugsgebiete.csv'):
            rows = csv_rows(files[name], ';')
            if not rows.fieldnames or 'Versicherer' not in rows.fieldnames:
                raise SourceChanged(f'Invalid conditions table: {name}')
            for row in rows:
                if row.get('Geschäftsjahr') != str(year):
                    raise SourceChanged('Condition year mismatch')
                db.execute('INSERT INTO conditions VALUES (?,?,?)',(name,str(int(row['Versicherer'])),json.dumps(row,ensure_ascii=False)))
        # Irregular activity table is retained verbatim, not silently discarded.
        db.execute('INSERT INTO conditions VALUES (?,?,?)',('Eingeschr.-Tät.gebiete.csv','*',json.dumps(files['Eingeschr.-Tät.gebiete.csv'].decode('utf-8-sig'))))
        db.execute('CREATE INDEX lookup ON premiums(canton,region,age,accident,deductible)')
        metadata = {'sourceUrl':source_url(year),'sourceLandingUrl':LANDING,'publisher':'Federal Office of Public Health (BAG/FOPH)',
                    'networkVerified':network_verified,'sourceSha256':hashlib.sha256(data).hexdigest(),'fetchedAt':iso(now),'expiresAt':iso(now + MAX_AGE),
                    'validFrom':f'{year}-01-01','validUntil':f'{year}-12-31','year':year,'rowCount':count,
                    'insurerCount':len(insurers),'insurerIds':sorted(insurers,key=int),
                    'cantonCount':len(cantons & CANTONS),'specialTerritoryCodes':sorted(cantons-CANTONS),
                    'priceBasis':'published-monthly-premium','currency':'CHF','derived':False,
                    'sourceDataLicense':'Not declared by dataset metadata; code license does not relicense source data.'}
        db.execute('INSERT INTO metadata VALUES (?)',(json.dumps(metadata),))
        db.commit()
        db.close()
        temp.replace(destination)
        return metadata
    except Exception:
        db.close()
        temp.unlink(missing_ok=True)
        raise

def validate_metadata(metadata, now=None):
    """Consumer guard: call again whenever serving a saved response."""
    now = now or datetime.now(timezone.utc)
    if not metadata.get('networkVerified'):
        raise SourceChanged('Local archive is unverified; run network refresh before displaying live rates')
    if now.year != metadata['year'] or metadata['validFrom'] != f"{now.year}-01-01" or metadata['validUntil'] != f"{now.year}-12-31":
        raise SourceChanged('Tariff year is not current; refresh for the current year')
    fetched = datetime.fromisoformat(metadata['fetchedAt'].replace('Z','+00:00'))
    expires = datetime.fromisoformat(metadata['expiresAt'].replace('Z','+00:00'))
    if fetched.tzinfo is None or expires.tzinfo is None:
        raise SourceChanged('Freshness timestamps must include time zone')
    if now < fetched:
        raise SourceChanged('Snapshot timestamp is in the future')
    if now >= expires or expires > fetched + MAX_AGE or expires <= fetched:
        raise SourceChanged('Snapshot expired or invalid; refresh before displaying rates')
    return True

def catalogue(db_path, filters=None, limit=100, now=None):
    """Read current exact published rows, with all dimensions and restrictions.
    A catalogue result is NOT a personalized offer/eligibility determination.
    """
    now = now or datetime.now(timezone.utc)
    db = sqlite3.connect(f'file:{Path(db_path).resolve()}?mode=ro',uri=True)
    try:
        metadata = json.loads(db.execute('SELECT data FROM metadata').fetchone()[0])
        validate_metadata(metadata, now)
        if not 1 <= limit <= 10000:
            raise ValueError('limit must be 1..10000')
        filters = filters or {}
        allowed = set('insurer canton region age accident tariff subgroup deductible'.split())
        if set(filters)-allowed:
            raise ValueError('Unknown filter')
        if filters.get('canton') and filters['canton'] not in CANTONS:
            raise ValueError('Select an ordinary Swiss canton')
        clauses = ['canton IN ('+','.join('?' for _ in CANTONS)+')']
        values = sorted(CANTONS)
        for key,val in filters.items():
            clauses.append(f'{key}=?')
            values.append(val)
        where = ' AND '.join(clauses)
        total = db.execute('SELECT count(*) FROM premiums WHERE '+where,values).fetchone()[0]
        names_path = ROOT / f"insurers-{metadata['year']}.json"
        names = json.loads(names_path.read_text())['names'] if names_path.exists() else {}
        results = []
        for insurer, premium, raw in db.execute('SELECT insurer,premium,raw FROM premiums WHERE '+where+' ORDER BY insurer,tariff,region,age,accident,subgroup,deductible LIMIT ?', values+[limit]):
            source_row = json.loads(raw)
            results.append({'providerId':f'ch-bag-{insurer}','providerName':names.get(insurer,f'BAG insurer {insurer}'),
                            'category':'basic-health-insurance','country':'CH','currency':'CHF',
                            'publishedMonthlyPremium':premium,'qualifier':'published-tariff','derived':False,
                            'personalizedQuote':False,'eligibilityVerified':False,'sourceRow':source_row})
        ids = sorted({r['sourceRow']['Versicherer'].lstrip('0') for r in results})
        conditions = []
        for insurer in ids:
            for kind,raw in db.execute('SELECT kind,raw FROM conditions WHERE insurer=?',(insurer,)):
                conditions.append({'table':kind,'row':json.loads(raw)})
        activity = db.execute("SELECT raw FROM conditions WHERE insurer='*'").fetchone()
        return {'metadata':metadata,'totalMatchingRows':total,'returnedRows':len(results),'offers':results,
                'conditions':conditions,'insurerActivityTableCsv':json.loads(activity[0]) if activity else None,
                'notice':'Published catalogue rows, not eligibility-confirmed quotes. Check municipal catchment, model access, age subgroup and insurer activity restrictions in the attached source tables. Premium is copied unchanged; no subsidies, rebates or taxes are calculated.'}
    finally:
        db.close()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db',default=str(ROOT/'data'/'premiums.sqlite'))
    commands=parser.add_subparsers(dest='command',required=True)
    refresh=commands.add_parser('refresh')
    refresh.add_argument('--year',type=int,default=datetime.now(timezone.utc).year)
    refresh.add_argument('--archive',type=Path,help='Import a downloaded official archive; source is still attributed to BAG')
    listing=commands.add_parser('list')
    for field in ('insurer','canton','region','age','accident','tariff','subgroup','deductible'):
        listing.add_argument('--'+field)
    listing.add_argument('--limit',type=int,default=100)
    args=parser.parse_args()
    try:
        if args.command=='refresh':
            if args.year != datetime.now(timezone.utc).year:
                raise SourceChanged('Only current-year live tariffs can be imported through the CLI')
            data=args.archive.read_bytes() if args.archive else download(source_url(args.year))
            output=import_archive(data,args.db,args.year,network_verified=not bool(args.archive))
            if args.archive:
                output['importNote']='Local archive imported; fetchedAt is import time, not proof of a network refresh.'
        else:
            output=catalogue(args.db,{k:getattr(args,k) for k in ('insurer','canton','region','age','accident','tariff','subgroup','deductible') if getattr(args,k) is not None},args.limit)
        print(json.dumps(output,ensure_ascii=False,indent=2))
    except (SourceChanged,ValueError,OSError,sqlite3.Error,zipfile.BadZipFile) as exc:
        print(json.dumps({'error':str(exc),'offers':[]}),file=sys.stderr)
        return 1
    return 0

if __name__=='__main__':
    raise SystemExit(main())
