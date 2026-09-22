import datetime as dt
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import providers

HBL='''<script>Sparkonto Extra 99%</script><h2>Sparen &amp; Vorsorgen</h2>
<table><tr><td>Sparkonto</td><td>0,025 %</td></tr>
<tr><td>Sparkonto Extra</td><td>0,250 % bis CHF 100'000<br>0,025 % über CHF 100'000</td></tr>
<tr><td>Aktionärssparkonto</td><td>0,500 % bis CHF 250'000<br>0,025 % über CHF 250'000</td></tr>
<tr><td>Jugend-Sparkonto</td><td>0,400 % bis CHF 20'000<br>0,025 % über CHF 20'000</td></tr>
<tr><td>Mietkautionssparkonto</td><td>0,000 %</td></tr>
<tr><td>Vorsorgekonto 3a</td><td>0,125 %</td></tr>
<tr><td>Freizügigkeitskonto 2. Säule</td><td>0,000 %</td></tr></table><p>Aare-Strategien</p>'''

class ProviderTests(unittest.TestCase):
    def test_rates_and_tiers_preserved_without_calculation(self):
        result=providers.parse('hbl',HBL,'2026-09-22T12:00:00+00:00')
        self.assertEqual(len(result['products']),7)
        product=result['products'][1]
        self.assertEqual([r['percent'] for r in product['published_rates']],['0.250','0.025'])
        self.assertIn("bis CHF 100'000",product['evidence_text'])
        self.assertFalse(product['derived'])
        self.assertFalse(product['personalized_quote'])
        self.assertEqual(result['products'][-1]['published_rates'][0]['percent'],'0.000')
    def test_layout_drift_fails_closed(self):
        with self.assertRaises(ValueError): providers.parse('hbl',HBL.replace('Vorsorgekonto 3a','Changed product'))
    def test_extra_value_fails_closed(self):
        with self.assertRaises(ValueError): providers.parse('hbl',HBL.replace('0,125 %','0,125 % 0,150 %'))
    def test_missing_rate_not_zero(self):
        with self.assertRaises(ValueError): providers.parse('hbl',HBL.replace('0,125 %','auf Anfrage'))
    def test_network_error_has_no_cached_rates(self):
        with patch('urllib.request.urlopen',side_effect=OSError('network down')):
            result=providers.fetch('hbl')
        self.assertEqual(result['status'],'error')
        self.assertEqual(result['products'],[])
    def test_scripts_ignored_and_split_decimal_supported(self):
        text=providers.plain_text('<script>9.99%</script><p>0,<b>4</b>00 %</p>')
        self.assertNotIn('9.99',text)
        self.assertEqual(len(providers.RATE.findall(text)),1)

    def test_freshness_rejects_future_and_stale(self):
        now=dt.datetime(2026,9,22,12,tzinfo=dt.timezone.utc)
        self.assertTrue(providers.is_fresh({'fetched_at':now.isoformat()},now))
        for hours in [-1,25]:
            timestamp=(now-dt.timedelta(hours=hours)).isoformat()
            self.assertFalse(providers.is_fresh({'fetched_at':timestamp},now))
        self.assertFalse(providers.is_fresh({'fetched_at':'2026-09-22T12:00:00'},now))
        self.assertFalse(providers.is_fresh({'fetched_at':now.isoformat(),'status':'error'},now))
    def test_atomic_write_replaces_complete_file(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'rates.json'
            target.write_text('old')
            providers.atomic_write(target,'{"new":true}\n')
            self.assertEqual(target.read_text(),'{"new":true}\n')
            self.assertEqual(len(list(Path(directory).iterdir())),1)

    def test_redirect_and_oversize_rejected(self):
        for url,payload in [('https://other.example/rates',b'<html/>'),
                            ('https://www.hbl.ch/de/zinssaetze-konditionen',b'x'*4000001)]:
            response=MagicMock()
            response.__enter__.return_value=response
            response.status=200
            response.headers={'Content-Type':'text/html'}
            response.geturl.return_value=url
            response.read.return_value=payload
            with patch('urllib.request.urlopen',return_value=response):
                result=providers.fetch('hbl')
            self.assertEqual(result['status'],'error')
            self.assertEqual(result['products'],[])

if __name__=='__main__': unittest.main()
