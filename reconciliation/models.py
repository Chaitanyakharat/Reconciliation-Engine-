from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid


class TransactionSource(models.TextChoices):
    """Transaction source types"""
    BANK = 'bank', 'Bank'
    GENERAL_LEDGER = 'gl', 'General Ledger'
    ACCOUNTS_PAYABLE = 'ap', 'Accounts Payable'
    PAYMENT_PROCESSOR = 'pp', 'Payment Processor'
    OTHER = 'other', 'Other'


class TransactionStatus(models.TextChoices):
    """Transaction status"""
    PENDING = 'pending', 'Pending'
    MATCHED = 'matched', 'Matched'
    UNMATCHED = 'unmatched', 'Unmatched'
    DUPLICATE = 'duplicate', 'Duplicate'
    ANOMALY = 'anomaly', 'Anomaly'


class MatchStatus(models.TextChoices):
    """Match status"""
    EXACT = 'exact', 'Exact Match'
    FUZZY = 'fuzzy', 'Fuzzy Match'
    COMPLEX = 'complex', 'Complex Match'
    MANUAL = 'manual', 'Manual Match'


class Transaction(models.Model):
    """Core transaction model for storing transaction data"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    date = models.DateField()
    description = models.CharField(max_length=500)
    reference = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    source = models.CharField(max_length=20, choices=TransactionSource.choices)
    vendor_name = models.CharField(max_length=300, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['source', 'date']),
            models.Index(fields=['amount', 'date']),
            models.Index(fields=['reference']),
        ]

    def __str__(self):
        return f"{self.source}: {self.amount} on {self.date}"


class Match(models.Model):
    """Match relationship between transactions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='source_matches'
    )
    target_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='target_matches'
    )
    match_type = models.CharField(max_length=20, choices=MatchStatus.choices)
    confidence = models.FloatField(
        validators=[MinValueValidator(0), models.MaxValueValidator(1)]
    )
    explanation = models.TextField()
    matched_fields = models.JSONField(default=list)
    rule_used = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matches'
        unique_together = ('source_transaction', 'target_transaction')
        indexes = [
            models.Index(fields=['source_transaction', 'target_transaction']),
            models.Index(fields=['confidence']),
        ]

    def __str__(self):
        return f"Match: {self.source_transaction.id} <-> {self.target_transaction.id}"


class Duplicate(models.Model):
    """Duplicate detection model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    original_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='original_duplicates'
    )
    duplicate_transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='duplicate_of'
    )
    similarity_score = models.FloatField(
        validators=[MinValueValidator(0), models.MaxValueValidator(1)]
    )
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'duplicates'

    def __str__(self):
        return f"Duplicate: {self.duplicate_transaction.id} of {self.original_transaction.id}"


class Anomaly(models.Model):
    """Anomaly detection model"""
    ANOMALY_TYPES = [
        ('round_amount', 'Round Amount'),
        ('unusual_date', 'Unusual Date'),
        ('missing_data', 'Missing Data'),
        ('encoding_issue', 'Encoding Issue'),
        ('format_issue', 'Format Issue'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name='anomalies'
    )
    anomaly_type = models.CharField(max_length=50, choices=ANOMALY_TYPES)
    description = models.TextField()
    severity = models.CharField(
        max_length=10,
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    )
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'anomalies'

    def __str__(self):
        return f"Anomaly: {self.anomaly_type} on {self.transaction.id}"


class Reconciliation(models.Model):
    """Reconciliation batch model"""
    RECONCILIATION_STATUS = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=RECONCILIATION_STATUS, default='pending')
    source_transactions = models.ManyToManyField(
        Transaction,
        related_name='source_reconciliations'
    )
    target_transactions = models.ManyToManyField(
        Transaction,
        related_name='target_reconciliations'
    )
    matches = models.ManyToManyField(Match, blank=True)
    total_transactions = models.IntegerField(default=0)
    matched_count = models.IntegerField(default=0)
    unmatched_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    anomaly_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'reconciliations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reconciliation: {self.name} ({self.status})"


class ReconciliationReport(models.Model):
    """Generated reconciliation report model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reconciliation = models.OneToOneField(
        Reconciliation,
        on_delete=models.CASCADE,
        related_name='report'
    )
    report_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reconciliation_reports'

    def __str__(self):
        return f"Report: {self.reconciliation.name}"
