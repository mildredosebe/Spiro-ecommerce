from django.conf import settings
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("waiting_for_payment", "Waiting for Payment"), 
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
    )

    order = models.ForeignKey(
        "order.Order",
        on_delete=models.CASCADE,
        related_name="payments",
    )

    phone_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    mpesa_checkout_request_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )

    merchant_request_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    mpesa_receipt_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        unique=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    stk_push_initiated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    paid_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    retry_count = models.IntegerField(
        default=0,
    )

    error_message = models.TextField(
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "spiro_payment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["mpesa_checkout_request_id"]),
        ]

    def __str__(self):
        return f"Payment #{self.pk} - {self.order.order_id} - {self.status}"

    @property
    def is_paid(self):
        """Check if payment is confirmed"""
        return self.status == "paid"

    @property
    def is_pending(self):
        """Check if payment is still pending"""
        return self.status in ["pending", "waiting_for_payment"]

    @property
    def is_failed(self):
        """Check if payment failed"""
        return self.status == "failed"

    def mark_as_waiting(self, initiated_at=None):
        """Mark payment as waiting for M-Pesa confirmation"""
        self.status = "waiting_for_payment"
        self.stk_push_initiated_at = initiated_at or timezone.now()
        self.save(update_fields=["status", "stk_push_initiated_at", "updated_at"])

    def mark_as_paid(self, receipt_number=None, paid_at=None):
        """Mark payment as successfully paid"""
        self.status = "paid"
        self.mpesa_receipt_number = receipt_number
        self.paid_at = paid_at or timezone.now()
        self.save(update_fields=["status", "mpesa_receipt_number", "paid_at", "updated_at"])

    def mark_as_failed(self, error_message=None):
        """Mark payment as failed"""
        self.status = "failed"
        self.error_message = error_message
        self.save(update_fields=["status", "error_message", "updated_at"])

    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1
        self.save(update_fields=["retry_count", "updated_at"])