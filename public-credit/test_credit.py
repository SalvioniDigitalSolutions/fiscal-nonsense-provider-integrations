import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from credit import parse, providers, SourceChanged, text_from_html, available_rates, atomic_write

class PublicCreditTests(unittest.TestCase):
    def setUp(self):
        self.p = providers()[0]
        self.now = '2026-09-22T10:00:00+00:00'
    def test_range_is_not_a_personalized_rate(self):
        row = parse(self.p, '<p>effektivem Jahreszins zwischen <b>4,9%</b> und 7,9%</p>', self.now)[0]
        self.assertEqual(('4.9','7.9'), (row['rate_min_percent'],row['rate_max_percent']))
        self.assertNotIn('rate_percent',row)
        self.assertFalse(row['personalized'])
        self.assertFalse(row['derived'])
    def test_conflicting_ranges_fail_closed(self):
        with self.assertRaises(SourceChanged):
            parse(self.p, 'effektivem Jahreszins zwischen 4,9% und 7,9% effektivem Jahreszins zwischen 5,9% und 7,9%', self.now)
    def test_duplicate_range_allowed(self):
        self.assertEqual(1,len(parse(self.p, 'effektivem Jahreszins zwischen 4,9% und 7,9% '*2,self.now)))
    def test_missing_range_and_script_data_fail_closed(self):
        for source in ['', '<script>effektivem Jahreszins zwischen 4,9% und 7,9%</script>', 'Leasing effektivem Jahreszins 4,9%']:
            with self.assertRaises(SourceChanged): parse(self.p,source,self.now)
    def test_reversed_range_rejected(self):
        with self.assertRaises(SourceChanged): parse(self.p, 'effektivem Jahreszins zwischen 9,9% und 4,9%',self.now)
    def test_cashgate_requires_complete_cohorts(self):
        p=next(p for p in providers() if p['id']=='cashgate')
        source='effektiven Jahreszins zwischen 3.9% und 9.9% '
        with self.assertRaises(SourceChanged): parse(p,source,self.now)
        grid="Laufzeit in Monaten/ Zinssatz ≤ 48 60 ≥ 72 ab CHF 4'500 Schweizer Pass C-Bewilligung Mit Wohneigentum 3.90% 4.90% 5.90% Ohne Wohneigentum 6.90% 7.90% 8.90% unter CHF 4'500 Schweizer Pass C-Bewilligung B-Bewilligung - 8.90% 9.90% 9.90%"
        rows=parse(p,source+grid,self.now)
        self.assertEqual(10,len(rows))
        self.assertEqual('3.90', rows[1]['rate_percent'])
        self.assertEqual('60', rows[2]['term_months_source_label'])
        self.assertEqual(False, rows[4]['eligibility_cohort']['homeownership'])
        self.assertEqual('not specified', rows[7]['eligibility_cohort']['homeownership'])
        with self.assertRaises(SourceChanged): parse(p,source+grid.replace('≤ 48','≤ 36'),self.now)
    def test_html_entities_and_hidden_styles(self):
        self.assertEqual('1 & 2',text_from_html('<style>bad</style><p>1 &amp; 2</p>'))

    def test_freshness_boundaries_and_future(self):
        now = datetime(2026,9,22,12,tzinfo=timezone.utc)
        row = {'provider_id': 'p', 'observed_at': now.isoformat(), 'freshness_ttl_hours': 24}
        document = {'status': 'ok', 'rates': [row], 'errors': []}
        self.assertEqual([row], available_rates(document,now))
        self.assertEqual([row], available_rates(document,now+timedelta(hours=24)))
        self.assertEqual([], available_rates(document,now+timedelta(hours=24,seconds=1)))
        self.assertEqual([], available_rates(document,now-timedelta(seconds=1)))
        row['freshness_ttl_hours']=999
        self.assertEqual([], available_rates(document,now+timedelta(hours=25)))
        row['freshness_ttl_hours']=1
        self.assertEqual([], available_rates(document,now+timedelta(hours=2)))
    def test_malformed_observations_fail_closed(self):
        for observed,ttl in [('bad',24),('2026-09-22T10:00:00',24),(None,24), (self.now,'NaN'),(self.now,-1)]:
            self.assertEqual([],available_rates({'status':'ok','rates':[{'observed_at':observed,'freshness_ttl_hours':ttl}]},self.now))
        with self.assertRaises(ValueError): available_rates({},'2026-09-22T10:00:00')
    def test_failed_provider_records_unavailable(self):
        row={'provider_id':'p','observed_at':self.now,'freshness_ttl_hours':24}
        self.assertEqual([],available_rates({'status':'partial','rates':[row],'errors':[{'provider_id':'p'}]},self.now))
        self.assertEqual([],available_rates({'status':'unavailable','rates':[row]},self.now))
    def test_atomic_write_replaces_and_cleans_failed_temporary(self):
        with TemporaryDirectory() as directory:
            path=Path(directory)/'rates.json'
            path.write_text('old')
            atomic_write(path,'new')
            self.assertEqual('new',path.read_text())
            with patch('credit.os.replace',side_effect=OSError('failure')):
                with self.assertRaises(OSError): atomic_write(path,'incomplete')
            self.assertEqual('new',path.read_text())
            self.assertEqual([path],list(Path(directory).iterdir()))

if __name__=='__main__': unittest.main()
