"""Data Validation and Cleaning Module"""
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Tuple, Any
import unicodedata

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates and cleans transaction data
    
    Handles multiple date formats, amount validation, text cleaning,
    duplicate detection, and anomaly flagging.
    """

    VALID_DATE_FORMATS = [
        '%Y-%m-%d',
        '%m/%d/%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%m-%d-%Y',
    ]

    @staticmethod
    def validate_transaction(data: Dict) -> Tuple[bool, Dict, List[str]]:
        """
        Validate transaction data

        Args:
            data: Transaction data dictionary

        Returns:
            Tuple of (is_valid: bool, cleaned_data: Dict, errors: List[str])
        """
        cleaned = {}
        errors = []

        # Validate amount
        try:
            amount = Decimal(str(data.get('amount', '')).strip())
            if amount <= 0:
                errors.append('Amount must be positive')
            else:
                cleaned['amount'] = amount
        except (InvalidOperation, ValueError):
            errors.append(f"Invalid amount format: {data.get('amount')}")

        # Validate date
        date_str = str(data.get('date', '')).strip()
        if not date_str:
            errors.append('Date is required')
        else:
            parsed_date = DataValidator.parse_date(date_str)
            if parsed_date:
                cleaned['date'] = parsed_date
            else:
                errors.append(f"Invalid date format: {date_str}")

        # Validate description
        description = str(data.get('description', '')).strip()
        if not description:
            errors.append('Description is required')
        else:
            cleaned['description'] = DataValidator.clean_text(description)

        # Validate reference (optional)
        reference = data.get('reference')
        if reference:
            cleaned['reference'] = str(reference).strip()

        # Validate source
        source = data.get('source')
        valid_sources = ['bank', 'gl', 'ap', 'pp', 'other']
        if source not in valid_sources:
            errors.append(f"Invalid source: {source}")
        else:
            cleaned['source'] = source

        # Vendor name (optional)
        vendor = data.get('vendor_name')
        if vendor:
            cleaned['vendor_name'] = DataValidator.clean_text(vendor)

        # Metadata
        cleaned['metadata'] = data.get('metadata', {})

        return len(errors) == 0, cleaned, errors

    @staticmethod
    def parse_date(date_str: str) -> Any:
        """Parse date from various formats
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Parsed date object or None if parsing failed
        """
        date_str = date_str.strip()

        for fmt in DataValidator.VALID_DATE_FORMATS:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove extra whitespace
        text = ' '.join(text.split())

        # Normalize unicode
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')

        return text

    @staticmethod
    def detect_duplicates(transactions: List[Dict]) -> List[Tuple[int, int, float]]:
        """Detect potential duplicates
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of (index1, index2, similarity_score) tuples
        """
        duplicates = []

        for i in range(len(transactions)):
            for j in range(i + 1, len(transactions)):
                t1 = transactions[i]
                t2 = transactions[j]

                # Check for exact duplicates
                if (t1.get('amount') == t2.get('amount') and
                    t1.get('date') == t2.get('date') and
                    t1.get('description') == t2.get('description')):
                    duplicates.append((i, j, 1.0))
                    continue

                # Check for similar transactions
                date_diff = abs((t1.get('date') - t2.get('date')).days) if t1.get('date') and t2.get('date') else 999
                amount_match = t1.get('amount') == t2.get('amount')

                if date_diff <= 1 and amount_match:
                    similarity = DataValidator._calculate_text_similarity(
                        t1.get('description', ''),
                        t2.get('description', '')
                    )
                    if similarity > 0.8:
                        duplicates.append((i, j, similarity))

        return duplicates

    @staticmethod
    def _calculate_text_similarity(s1: str, s2: str) -> float:
        """Calculate text similarity using SequenceMatcher"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    @staticmethod
    def detect_anomalies(transaction: Dict) -> List[Tuple[str, str, str]]:
        """Detect anomalies in transaction
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            List of (anomaly_type, description, severity) tuples
        """
        anomalies = []

        # Check for round amounts
        amount = transaction.get('amount')
        if amount and amount % 1000 == 0:
            anomalies.append(('round_amount', f'Round amount detected: {amount}', 'low'))

        # Check for unusual dates
        date = transaction.get('date')
        if date:
            today = datetime.now().date()
            if date > today:
                anomalies.append(('unusual_date', 'Future date detected', 'medium'))
            elif (today - date).days > 365 * 5:
                anomalies.append(('unusual_date', 'Very old date detected', 'low'))

        # Check for missing data
        if not transaction.get('reference'):
            anomalies.append(('missing_data', 'Missing reference number', 'low'))
        if not transaction.get('vendor_name'):
            anomalies.append(('missing_data', 'Missing vendor name', 'low'))

        # Check for encoding issues
        desc = str(transaction.get('description', ''))
        if '\ufffd' in desc:
            anomalies.append(('encoding_issue', 'Invalid unicode characters detected', 'medium'))

        return anomalies
