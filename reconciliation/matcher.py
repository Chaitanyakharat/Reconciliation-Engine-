"""Transaction Matching Engine"""
import logging
from typing import List, Dict, Tuple, Optional
from decimal import Decimal
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class TransactionMatcher:
    """Matches transactions using various strategies
    
    Supports exact matching, fuzzy matching with tolerance, and complex
    multi-transaction matching with confidence scoring.
    """

    def __init__(self, amount_tolerance: float = 0.5, date_tolerance_days: int = 2):
        """
        Initialize TransactionMatcher

        Args:
            amount_tolerance: Percentage tolerance for amount differences (default: 0.5%)
            date_tolerance_days: Number of days tolerance for date differences (default: 2)
        """
        self.amount_tolerance = amount_tolerance
        self.date_tolerance_days = date_tolerance_days

    def match_exact(self, source: Dict, target: Dict) -> Tuple[bool, float, str]:
        """
        Exact match: amount, date, reference must all match

        Args:
            source: Source transaction dictionary
            target: Target transaction dictionary

        Returns:
            Tuple of (matched: bool, confidence: float, explanation: str)
        """
        # Amount must match exactly
        if source['amount'] != target['amount']:
            return False, 0.0, "Amount does not match"

        # Date must match exactly
        if source['date'] != target['date']:
            return False, 0.0, "Date does not match"

        # Reference must match if both exist
        source_ref = source.get('reference')
        target_ref = target.get('reference')

        if source_ref and target_ref and source_ref != target_ref:
            return False, 0.0, "Reference does not match"

        explanation = "Exact match: amount, date"
        if source_ref and target_ref:
            explanation += ", reference"

        return True, 1.0, explanation

    def match_fuzzy(self, source: Dict, target: Dict) -> Tuple[bool, float, str]:
        """
        Fuzzy match: amount within tolerance, date within window, description similar

        Args:
            source: Source transaction dictionary
            target: Target transaction dictionary

        Returns:
            Tuple of (matched: bool, confidence: float, explanation: str)
        """
        explanations = []
        scores = []

        # Check amount
        source_amount = Decimal(str(source['amount']))
        target_amount = Decimal(str(target['amount']))

        if source_amount == 0:
            return False, 0.0, "Source amount is zero"

        amount_diff_percent = abs((target_amount - source_amount) / source_amount) * 100

        if amount_diff_percent <= self.amount_tolerance:
            score = 1.0 - (amount_diff_percent / 100)
            scores.append(score)
            if amount_diff_percent == 0:
                explanations.append("Amount exact")
            else:
                explanations.append(f"Amount within {amount_diff_percent:.2f}%")
        else:
            return False, 0.0, f"Amount difference {amount_diff_percent:.2f}% exceeds tolerance"

        # Check date
        date_diff = abs((target['date'] - source['date']).days)

        if date_diff <= self.date_tolerance_days:
            score = 1.0 - (date_diff / (self.date_tolerance_days * 2))
            scores.append(score)
            if date_diff == 0:
                explanations.append("Date exact")
            else:
                explanations.append(f"Date within {date_diff} days")
        else:
            return False, 0.0, f"Date difference {date_diff} days exceeds tolerance"

        # Check description similarity
        source_desc = str(source.get('description', '')).lower()
        target_desc = str(target.get('description', '')).lower()

        if source_desc and target_desc:
            similarity = SequenceMatcher(None, source_desc, target_desc).ratio()
            scores.append(similarity)
            explanations.append(f"Description {similarity:.0%} similar")

        confidence = sum(scores) / len(scores) if scores else 0.0
        explanation = ", ".join(explanations)

        return confidence > 0.6, confidence, explanation

    def match_complex(
        self, source: Dict, targets: List[Dict]
    ) -> Tuple[bool, List[int], float, str]:
        """
        Complex match: one source matches multiple targets or vice versa

        Args:
            source: Source transaction dictionary
            targets: List of target transaction dictionaries

        Returns:
            Tuple of (matched: bool, target_indices: List[int], confidence: float, explanation: str)
        """
        total_target_amount = sum(t['amount'] for t in targets)

        if source['amount'] != total_target_amount:
            tolerance_amount = source['amount'] * (1 + self.amount_tolerance / 100)
            if total_target_amount > tolerance_amount:
                return False, [], 0.0, "Total target amount exceeds tolerance"

        # Check date range
        target_dates = [t['date'] for t in targets]
        date_range = max(target_dates) - min(target_dates)

        if date_range.days > self.date_tolerance_days:
            return False, [], 0.0, f"Target date range {date_range.days} exceeds tolerance"

        # Check if source date is within target date range
        if source['date'] < min(target_dates) or source['date'] > max(target_dates):
            return False, [], 0.0, "Source date not in target date range"

        matched_indices = list(range(len(targets)))
        confidence = 0.7 if total_target_amount == source['amount'] else 0.5
        explanation = f"Complex match: 1 source to {len(targets)} targets"

        return True, matched_indices, confidence, explanation

    def find_best_match(
        self,
        source: Dict,
        candidates: List[Dict],
        match_threshold: float = 0.6
    ) -> Optional[Tuple[int, float, str, str]]:
        """
        Find best matching candidate

        Args:
            source: Source transaction dictionary
            candidates: List of candidate transaction dictionaries
            match_threshold: Minimum confidence threshold for match

        Returns:
            Tuple of (candidate_index, confidence, explanation, match_type) or None
        """
        best_match = None
        best_score = 0.0
        best_type = None
        best_explanation = None

        for idx, candidate in enumerate(candidates):
            # Try exact match
            matched, confidence, explanation = self.match_exact(source, candidate)
            if matched and confidence > best_score:
                best_match = idx
                best_score = confidence
                best_type = 'exact'
                best_explanation = explanation
                continue

            # Try fuzzy match
            matched, confidence, explanation = self.match_fuzzy(source, candidate)
            if matched and confidence > best_score:
                best_match = idx
                best_score = confidence
                best_type = 'fuzzy'
                best_explanation = explanation

        if best_match is not None and best_score >= match_threshold:
            return best_match, best_score, best_explanation, best_type

        return None

    def match_batch(
        self,
        sources: List[Dict],
        targets: List[Dict],
        match_threshold: float = 0.6
    ) -> Dict:
        """
        Match batch of source transactions to targets

        Args:
            sources: List of source transactions
            targets: List of target transactions
            match_threshold: Minimum confidence threshold

        Returns:
            Dict with matched, unmatched_sources, unmatched_targets, and duplicates
        """
        matches = []
        unmatched = []
        duplicates = []
        matched_target_indices = set()

        for source_idx, source in enumerate(sources):
            # Find candidates
            candidates = [
                (idx, t) for idx, t in enumerate(targets)
                if idx not in matched_target_indices
            ]

            if not candidates:
                unmatched.append({
                    'source_index': source_idx,
                    'reason': 'No available candidates'
                })
                continue

            candidate_data = [t for _, t in candidates]
            candidate_indices = [idx for idx, _ in candidates]

            result = self.find_best_match(source, candidate_data, match_threshold)

            if result:
                matched_idx, confidence, explanation, match_type = result
                actual_idx = candidate_indices[matched_idx]

                matches.append({
                    'source_index': source_idx,
                    'target_index': actual_idx,
                    'confidence': confidence,
                    'explanation': explanation,
                    'match_type': match_type
                })

                matched_target_indices.add(actual_idx)
            else:
                unmatched.append({
                    'source_index': source_idx,
                    'reason': 'No suitable match found'
                })

        # Identify unmatched targets
        unmatched_targets = [
            {'target_index': idx}
            for idx in range(len(targets))
            if idx not in matched_target_indices
        ]

        return {
            'matches': matches,
            'unmatched_sources': unmatched,
            'unmatched_targets': unmatched_targets,
            'duplicates': duplicates,
        }
