import importlib.util
import json
from pathlib import Path
import sys
import unittest
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mortgage_rates', ROOT / 'rates.py')
rates = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rates)
NOW = datetime(2026, 9, 22, 12, tzinfo=timezone.utc)

class AdapterTests(unittest.TestCase):
    def test_every_adapter_preserves_exact_synthetic_rate_and_terms(self):
        total = 0
        for provider in rates.providers():
            with self.subTest(provider=provider['id']):
                html = (ROOT / 'tests/fixtures' / (provider['id'] + '.html')).read_text()
                result = rates.extract(provider, html, NOW)
                self.assertEqual(len(result), sum(len(s['terms']) for s in provider['sections']))
                self.assertEqual({r['annualRatePercent'] for r in result}, {'7.123'})
                self.assertTrue(all(not r['derived'] and not r['binding'] for r in result))
                self.assertTrue(all(r['sourceUrl'] == provider['url'] for r in result))
                total += len(result)
        self.assertEqual(total, 220)

    def test_missing_duplicate_or_unexpected_term_fails_closed(self):
        p = next(p for p in rates.providers() if p['id'] == 'zkb')
        html = (ROOT / 'tests/fixtures/zkb.html').read_text()
        for malformed in (html.replace('2 Jahre', 'unknown'), html.replace('3 Jahre', '2 Jahre'), html.replace('2 Jahre', '22 Jahre'), html.replace('7.123', '999.123', 1)):
            with self.assertRaises(rates.SourceChanged):
                rates.extract(p, malformed, NOW)

    def test_expired_published_table_fails_closed(self):
        p = next(p for p in rates.providers() if p['id'] == 'bvk')
        html = (ROOT / 'tests/fixtures/bvk.html').read_text().replace('2099', '2025')
        with self.assertRaises(rates.SourceChanged):
            rates.extract(p, html, NOW)

    def test_decimal_comma_preserves_precision(self):
        p = next(p for p in rates.providers() if p['id'] == 'zkb')
        html = (ROOT / 'tests/fixtures/zkb.html').read_text().replace('7.123', '1,230')
        self.assertEqual(rates.extract(p, html, NOW)[0]['annualRatePercent'], '1.230')

    def test_no_fallback_on_fetch_failure(self):
        def failure(p): raise TimeoutError('synthetic timeout')
        output = rates.collect(rates.providers()[:1], loader=failure)
        self.assertEqual(output['rates'], [])
        self.assertEqual(output['providers'][0]['status'], 'unavailable')

    def test_client_expiry_and_exact_term_filter(self):
        p = next(p for p in rates.providers() if p['id'] == 'zkb')
        result = {'rates': rates.extract(p, (ROOT / 'tests/fixtures/zkb.html').read_text(), NOW)}
        self.assertEqual(len(rates.available_rates(result, NOW, term=5)), 1)
        self.assertEqual(rates.available_rates(result, NOW, term=16), [])
        self.assertEqual(rates.available_rates(result, NOW + timedelta(hours=24)), [])
        self.assertEqual(rates.available_rates(result, NOW - timedelta(seconds=1)), [])

    def test_ca_next_bank_uses_swiss_column_only(self):
        p = next(p for p in rates.providers() if p['id'] == 'ca-nextbank')
        html = (ROOT / 'tests/fixtures/ca-nextbank.html').read_text()
        self.assertTrue(all(r['annualRatePercent'] == '7.123' for r in rates.extract(p, html, NOW)))
        self.assertIn('Ab 4.20%', html)

    def test_changed_country_or_rate_column_headings_fail_closed(self):
        for provider_id, before, after in [('ca-nextbank', 'Schweiz**', 'Frankreich**'), ('migros', 'Taux d’intérêt standard', 'New pricing column')]:
            p = next(p for p in rates.providers() if p['id'] == provider_id)
            html = (ROOT / 'tests/fixtures' / (provider_id + '.html')).read_text()
            with self.assertRaises(rates.SourceChanged):
                rates.extract(p, html.replace(before, after), NOW)

    def test_markup_and_script_numbers_do_not_inject_rates(self):
        p = next(p for p in rates.providers() if p['id'] == 'zkb')
        html = (ROOT / 'tests/fixtures/zkb.html').read_text()
        self.assertEqual(len(rates.extract(p, '<script>2 Jahre 0.01%</script>' + html, NOW)), 14)

if __name__ == '__main__': unittest.main()
