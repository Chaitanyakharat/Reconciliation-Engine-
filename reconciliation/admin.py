"""Django Admin Configuration"""
from django.contrib import admin
from .models import (
    Transaction, Match, Duplicate,
    Anomaly, Reconciliation, ReconciliationReport
)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transaction model"""
    list_display = ('id', 'amount', 'date', 'source', 'status', 'created_at')
    list_filter = ('source', 'status', 'date')
    search_fields = ('description', 'reference', 'vendor_name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    """Admin interface for Match model"""
    list_display = ('id', 'source_transaction', 'target_transaction', 'confidence', 'match_type')
    list_filter = ('match_type', 'confidence')
    search_fields = ('rule_used',)
    readonly_fields = ('id', 'created_at')


@admin.register(Duplicate)
class DuplicateAdmin(admin.ModelAdmin):
    """Admin interface for Duplicate model"""
    list_display = ('id', 'original_transaction', 'duplicate_transaction', 'similarity_score')
    readonly_fields = ('detected_at',)


@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    """Admin interface for Anomaly model"""
    list_display = ('id', 'transaction', 'anomaly_type', 'severity')
    list_filter = ('anomaly_type', 'severity')


@admin.register(Reconciliation)
class ReconciliationAdmin(admin.ModelAdmin):
    """Admin interface for Reconciliation model"""
    list_display = ('id', 'name', 'status', 'matched_count', 'unmatched_count', 'created_at')
    list_filter = ('status', 'created_at')
    readonly_fields = ('id', 'created_at', 'started_at', 'completed_at')


@admin.register(ReconciliationReport)
class ReconciliationReportAdmin(admin.ModelAdmin):
    """Admin interface for ReconciliationReport model"""
    list_display = ('id', 'reconciliation', 'created_at')
    readonly_fields = ('id', 'created_at', 'report_data')
