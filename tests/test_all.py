"""Comprehensive Test Suite for Financial Reconciliation Engine"""
import pytest
from datetime import date
from decimal import Decimal
from reconciliation.matcher import TransactionMatcher
from reconciliation.validators import DataValidator
from reconciliation.reporting import ReportGenerator


class TestTransactionMatcher:
    """Test TransactionMatcher class"""

    def test_exact_match_success(self):
        """Test successful exact match"""
        matcher = TransactionMatcher()
        source = {
            'amount': Decimal('100.00'),
            'date': date(2026, 5, 12),
            'reference': 'REF001'
        }
        target = {
            'amount': Decimal('100.00'),
            'date': date(2026, 5, 12),
            'reference': 'REF001'
        }
        matched, confidence, explanation = matcher.match_exact(source, target)
        assert matched is True
        assert confidence == 1.0
        assert 'exact' in explanation.lower()

    def test_exact_match_amount_mismatch(self):
        """Test exact match with amount mismatch"""
        matcher = TransactionMatcher()
        source = {'amount': Decimal('100.00'), 'date': date(2026, 5, 12)}
        target = {'amount': Decimal('101.00'), 'date': date(2026, 5, 12)}
        matched, confidence, _ = matcher.match_exact(source, target)
        assert matched is False
        assert confidence == 0.0

    def test_exact_match_date_mismatch(self):
        """Test exact match with date mismatch"""
        matcher = TransactionMatcher()
        source = {'amount': Decimal('100.00'), 'date': date(2026, 5, 12)}
        target = {'amount': Decimal('100.00'), 'date': date(2026, 5, 13)}
        matched, confidence, _ = matcher.match_exact(source, target)
        assert matched is False

    def test_fuzzy_match_within_tolerance(self):
        """Test fuzzy match within tolerance"""
        matcher = TransactionMatcher(amount_tolerance=1.0, date_tolerance_days=2)
        source = {
            'amount': Decimal('100.00'),
            'date': date(2026, 5, 12),
            'description': 'Payment ABC'
        }
        target = {
            'amount': Decimal('100.50'),
            'date': date(2026, 5, 13),
            'description': 'Payment ABC'
        }
        matched, confidence, _ = matcher.match_fuzzy(source, target)
        assert matched is True
        assert confidence > 0.6

    def test_fuzzy_match_exceeds_tolerance(self):
        """Test fuzzy match exceeding amount tolerance"""
        matcher = TransactionMatcher(amount_tolerance=0.5)
        source = {'amount': Decimal('100.00'), 'date': date(2026, 5, 12)}
        target = {'amount': Decimal('102.00'), 'date': date(2026, 5, 12)}
        matched, confidence, _ = matcher.match_fuzzy(source, target)
        assert matched is False

    def test_batch_match_success(self):
        """Test batch matching"""
        matcher = TransactionMatcher()
        sources = [
            {
                'amount': Decimal('100.00'),
                'date': date(2026, 5, 12),
                'description': 'Payment 1',
                'reference': 'S001'
            },
            {
                'amount': Decimal('200.00'),
                'date': date(2026, 5, 13),
                'description': 'Payment 2',
                'reference': 'S002'
            }
        ]
        targets = [
            {
                'amount': Decimal('100.00'),
                'date': date(2026, 5, 12),
                'description': 'Payment 1',
                'reference': 'T001'
            },
            {
                'amount': Decimal('200.00'),
                'date': date(2026, 5, 13),
                'description': 'Payment 2',
                'reference': 'T002'
            }
        ]
        result = matcher.match_batch(sources, targets)
        assert len(result['matches']) == 2
        assert len(result['unmatched_sources']) == 0


class TestDataValidator:
    """Test DataValidator class"""

    def test_valid_transaction(self):
        """Test validation of valid transaction"""
        data = {
            'amount': '100.00',
            'date': '2026-05-12',
            'description': 'Test payment',
            'source': 'bank',
            'reference': 'REF001'
        }
        is_valid, cleaned, errors = DataValidator.validate_transaction(data)
        assert is_valid is True
        assert len(errors) == 0
        assert cleaned['amount'] == Decimal('100.00')

    def test_invalid_amount(self):
        """Test validation with invalid amount"""
        data = {
            'amount': 'invalid',
            'date': '2026-05-12',
            'description': 'Test',
            'source': 'bank'
        }
        is_valid, cleaned, errors = DataValidator.validate_transaction(data)
        assert is_valid is False
        assert len(errors) > 0

    def test_negative_amount(self):
        """Test validation with negative amount"""
        data = {
            'amount': '-100.00',
            'date': '2026-05-12',
            'description': 'Test',
            'source': 'bank'
        }
        is_valid, cleaned, errors = DataValidator.validate_transaction(data)
        assert is_valid is False

    def test_parse_date_iso_format(self):
        """Test date parsing in ISO format"""
        parsed = DataValidator.parse_date('2026-05-12')
        assert parsed == date(2026, 5, 12)

    def test_parse_date_us_format(self):
        """Test date parsing in US format"""
        parsed = DataValidator.parse_date('05/12/2026')
        assert parsed == date(2026, 5, 12)

    def test_parse_date_invalid(self):
        """Test date parsing with invalid format"""
        parsed = DataValidator.parse_date('invalid')
        assert parsed is None

    def test_clean_text_whitespace(self):
        """Test text cleaning for whitespace"""
        text = '  Test  Text  '
        cleaned = DataValidator.clean_text(text)
        assert cleaned == 'Test Text'

    def test_detect_anomalies_round_amount(self):
        """Test anomaly detection for round amount"""
        transaction = {
            'amount': Decimal('5000.00'),
            'date': date(2026, 5, 12),
            'description': 'Payment'
        }
        anomalies = DataValidator.detect_anomalies(transaction)
        assert any(a[0] == 'round_amount' for a in anomalies)

    def test_detect_anomalies_missing_reference(self):
        """Test anomaly detection for missing reference"""
        transaction = {
            'amount': Decimal('100.00'),
            'date': date(2026, 5, 12),
            'description': 'Payment'
        }
        anomalies = DataValidator.detect_anomalies(transaction)
        assert any(a[0] == 'missing_data' for a in anomalies)


class TestReportGenerator:
    """Test ReportGenerator class"""

    def test_generate_report(self):
        """Test report generation"""
        gen = ReportGenerator()
        matches = [
            {
                'source_index': 0,
                'target_index': 0,
                'confidence': 1.0,
                'match_type': 'exact',
                'explanation': 'Exact match',
                'matched_fields': ['amount', 'date']
            }
        ]
        report = gen.generate_report(matches, [], [], [], [])
        assert report['summary']['matched'] == 1
        assert report['summary']['match_percentage'] == 100.0

    def test_export_json(self):
        """Test JSON export"""
        gen = ReportGenerator()
        matches = [{'source_index': 0, 'target_index': 0, 'confidence': 1.0, 'match_type': 'exact'}]
        gen.generate_report(matches, [], [], [], [])
        json_str = gen.export_json()
        assert isinstance(json_str, str)
        assert 'matched' in json_str

    def test_print_summary(self):
        """Test summary printing"""
        gen = ReportGenerator()
        matches = [{'source_index': 0, 'target_index': 0, 'confidence': 1.0, 'match_type': 'exact'}]
        gen.generate_report(matches, [], [], [], [])
        summary = gen.print_summary()
        assert isinstance(summary, str)
        assert 'RECONCILIATION REPORT' in summary


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=reconciliation'])
