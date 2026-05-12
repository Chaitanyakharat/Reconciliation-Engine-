"""Report Generation Module"""
import json
import logging
from typing import Dict, List, Any
from datetime import datetime
import csv
from io import StringIO

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generates reconciliation reports in multiple formats
    
    Supports JSON and CSV export with human-readable summaries.
    """

    def __init__(self):
        """Initialize ReportGenerator"""
        self.report_data = {}

    def generate_report(
        self,
        matches: List[Dict],
        unmatched_sources: List[Dict],
        unmatched_targets: List[Dict],
        duplicates: List[Dict],
        anomalies: List[Dict]
    ) -> Dict[str, Any]:
        """
        Generate comprehensive reconciliation report

        Args:
            matches: List of matched transaction pairs
            unmatched_sources: List of unmatched source transactions
            unmatched_targets: List of unmatched target transactions
            duplicates: List of detected duplicates
            anomalies: List of detected anomalies

        Returns:
            Report dictionary with summary and detailed information
        """
        total_transactions = len(matches) * 2 + len(unmatched_sources) + len(unmatched_targets)

        report = {
            'summary': {
                'timestamp': datetime.now().isoformat(),
                'total_transactions': total_transactions,
                'matched': len(matches),
                'unmatched_sources': len(unmatched_sources),
                'unmatched_targets': len(unmatched_targets),
                'duplicates': len(duplicates),
                'anomalies': len(anomalies),
                'match_percentage': (len(matches) / max(total_transactions, 1)) * 100,
            },
            'matched_pairs': self._format_matches(matches),
            'unmatched': {
                'sources': unmatched_sources,
                'targets': unmatched_targets,
            },
            'duplicates': duplicates,
            'anomalies': anomalies,
        }

        self.report_data = report
        return report

    def _format_matches(self, matches: List[Dict]) -> List[Dict]:
        """Format matches for report
        
        Args:
            matches: List of match dictionaries
            
        Returns:
            Formatted matches list
        """
        formatted = []

        for i, match in enumerate(matches, 1):
            formatted.append({
                'id': i,
                'source_index': match.get('source_index'),
                'target_index': match.get('target_index'),
                'confidence': round(match.get('confidence', 0), 4),
                'match_type': match.get('match_type'),
                'explanation': match.get('explanation'),
                'matched_fields': match.get('matched_fields', []),
            })

        return formatted

    def export_json(self) -> str:
        """Export report as JSON
        
        Returns:
            JSON string representation of report
        """
        return json.dumps(self.report_data, indent=2, default=str)

    def export_csv(self) -> str:
        """Export report as CSV
        
        Returns:
            CSV string representation of matched pairs
        """
        output = StringIO()
        writer = csv.writer(output)

        # Headers
        writer.writerow([
            'Match ID', 'Source Index', 'Target Index',
            'Confidence', 'Match Type', 'Explanation'
        ])

        # Rows
        for match in self.report_data.get('matched_pairs', []):
            writer.writerow([
                match['id'],
                match['source_index'],
                match['target_index'],
                match['confidence'],
                match['match_type'],
                match['explanation'],
            ])

        return output.getvalue()

    def print_summary(self) -> str:
        """Print human-readable summary
        
        Returns:
            Formatted summary string
        """
        summary = self.report_data.get('summary', {})

        lines = [
            "=" * 60,
            "RECONCILIATION REPORT",
            "=" * 60,
            f"Timestamp: {summary.get('timestamp')}",
            f"Total Transactions: {summary.get('total_transactions')}",
            f"Matched: {summary.get('matched')} ({summary.get('match_percentage', 0):.1f}%)",
            f"Unmatched Sources: {summary.get('unmatched_sources')}",
            f"Unmatched Targets: {summary.get('unmatched_targets')}",
            f"Duplicates: {summary.get('duplicates')}",
            f"Anomalies: {summary.get('anomalies')}",
            "=" * 60,
        ]

        return "\n".join(lines)
