from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class AuditRun(models.Model):
    class Kind(models.TextChoices):
        PAGES = "pages", _("Page inspection")

    class Status(models.TextChoices):
        RUNNING = "running", _("Running")
        SUCCEEDED = "succeeded", _("Succeeded")
        PARTIAL = "partial", _("Partly failed")
        FAILED = "failed", _("Failed")

    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.PAGES)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.RUNNING, db_index=True
    )
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    pages_inspected = models.PositiveIntegerField(default=0)
    pages_failed = models.PositiveIntegerField(default=0)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-started_at"]
        get_latest_by = "started_at"

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.started_at:%Y-%m-%d %H:%M}"


class Finding(models.Model):
    class Severity(models.TextChoices):
        ERROR = "error", _("Error")
        WARNING = "warning", _("Warning")

    run = models.ForeignKey(AuditRun, on_delete=models.CASCADE, related_name="findings")
    page = models.ForeignKey(
        "wagtailcore.Page", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    locale = models.ForeignKey(
        "wagtailcore.Locale", null=True, on_delete=models.SET_NULL, related_name="+"
    )
    code = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(max_length=8, choices=Severity.choices, db_index=True)
    message = models.TextField()
    url = models.URLField(blank=True, max_length=500)
    fingerprint = models.CharField(max_length=255, blank=True)
    first_seen_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-first_seen_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["code", "page", "locale", "fingerprint"],
                condition=Q(resolved_at__isnull=True),
                name="audits_unique_open_finding",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} on page {self.page_id}"

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None
