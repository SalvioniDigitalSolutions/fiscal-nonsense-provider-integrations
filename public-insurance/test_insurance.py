import csv
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import insurance as api

NOW = datetime(2026,9,22,tzinfo=timezone.utc)

def archive(premium='501.1',year=2026,empty=False):
    output=io.BytesIO()
    row=['8','AG','CH',str(year),'2025','PR-REG CH0','AKL-ERW','MIT-UNF','01_016','TAR-HAM','','FRAST1','FRA-300',premium,'0','1','Gesundheitspraxisversicherung']
    text=io.StringIO(); writer=csv.writer(text);writer.writerow(api.HEADERS)
    if not empty: writer.writerow(row)
    with zipfile.ZipFile(output,'w') as z:
        z.writestr('Prämien_CH.csv',text.getvalue())
        z.writestr('Tarife.csv',f'Versicherer;Geschäftsjahr;Kategorie;Tarif;Name_DE\n0008;{year};MOD;01_016;Gesundheitspraxisversicherung\n')
        z.writestr('Einzugsgebiete.csv',f'Versicherer;Geschäftsjahr;Eingeschränkt;Gemeinden-BFS\n0008;{year};J;1001\n')
        z.writestr('Eingeschr.-Tät.gebiete.csv','G_ID;AG\n0008;1.1\n')
    return output.getvalue()

class InsuranceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'rates.sqlite'
    def tearDown(self): self.tmp.cleanup()
    def seed(self,**kwargs): return api.import_archive(archive(**kwargs),self.db,2026,NOW,True)
    def test_exact_amount_and_conditions(self):
        self.seed(); out=api.catalogue(self.db,{'canton':'AG','age':'AKL-ERW'},now=NOW)
        self.assertEqual(out['offers'][0]['publishedMonthlyPremium'],'501.1')
        self.assertEqual(out['offers'][0]['providerName'],'CSS')
        self.assertFalse(out['offers'][0]['eligibilityVerified'])
        self.assertEqual(out['conditions'][1]['row']['Gemeinden-BFS'],'1001')
        self.assertEqual(out['totalMatchingRows'],1)
    def test_wrong_year_atomic(self):
        self.seed()
        with self.assertRaises(api.SourceChanged):self.seed(year=2027)
        self.assertEqual(api.catalogue(self.db,now=NOW)['totalMatchingRows'],1)
    def test_empty_source_atomic(self):
        self.seed()
        with self.assertRaises(api.SourceChanged):self.seed(empty=True)
        self.assertEqual(api.catalogue(self.db,now=NOW)['totalMatchingRows'],1)
    def test_expired_not_live(self):
        self.seed()
        with self.assertRaises(api.SourceChanged):api.catalogue(self.db,now=NOW+timedelta(days=1))
    def test_next_year_not_live(self):
        self.seed()
        with self.assertRaises(api.SourceChanged):api.catalogue(self.db,now=datetime(2027,1,1,tzinfo=timezone.utc))
    def test_local_file_not_live(self):
        api.import_archive(archive(),self.db,2026,NOW)
        with self.assertRaises(api.SourceChanged):api.catalogue(self.db,now=NOW)
    def test_invalid_prices(self):
        for amount in ('NaN','Infinity','-1','999999'):
            with self.assertRaises(api.SourceChanged):self.seed(premium=amount)
    def test_filter_no_interpolation(self):
        self.seed();out=api.catalogue(self.db,{'deductible':'FRA-2000'},now=NOW)
        self.assertEqual(out['offers'],[])
    def test_future_snapshot_rejected(self):
        meta=self.seed()
        with self.assertRaises(api.SourceChanged):api.validate_metadata(meta,NOW-timedelta(seconds=1))
    def test_extended_expiry_rejected(self):
        meta=self.seed();meta["expiresAt"]=api.iso(NOW+timedelta(days=2))
        with self.assertRaises(api.SourceChanged):api.validate_metadata(meta,NOW)
    def test_unknown_filter(self):
        self.seed()
        with self.assertRaises(ValueError):api.catalogue(self.db,{'income':'1'},now=NOW)
    def test_missing_restrictions_fails(self):
        with self.assertRaises((api.SourceChanged,zipfile.BadZipFile)):api.archive_files(b'not a zip')

if __name__=='__main__':unittest.main()
