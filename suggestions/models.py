from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Task(models.TextChoices):
    SEO_TITLE = "seo_title", _("SEO title")
    META_DESCRIPTION = "meta_description", _("Meta description")
    TRANSLATION = "translation", _("Translation")


class ProviderCall(models.Model):
    task = models.CharField(_("task"), max_length=32, choices=Task.choices)
    provider = models.CharField(_("provider"), max_length=255)
    model_name = models.CharField(_("model"), max_length=128, blank=True)
    prompt = models.TextField(_("prompt"))
    response = models.TextField(_("response"), blank=True)
    error = models.CharField(_("error"), max_length=255, blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("requested by"),
    )
    created_at = models.DateTimeField(_("created"), auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_task_display()} via {self.provider}"

    @property
    def succeeded(self) -> bool:
        return not self.error


class Suggestion(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending review")
        APPROVED = "approved", _("Approved as a draft")
        REJECTED = "rejected", _("Rejected")

    finding = models.ForeignKey(
        "audits.Finding",
        on_delete=models.CASCADE,
        related_name="suggestions",
        verbose_name=_("finding"),
    )
    task = models.CharField(_("task"), max_length=32, choices=Task.choices)
    status = models.CharField(
        _("status"),
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    proposed_text = models.TextField(_("proposed text"))
    call = models.ForeignKey(
        ProviderCall,
        on_delete=models.PROTECT,
        related_name="suggestions",
        verbose_name=_("model call"),
    )
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("reviewed by"),
    )
    reviewed_at = models.DateTimeField(_("reviewed"), null=True, blank=True)
    review_note = models.TextField(_("review note"), blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["finding"],
                condition=models.Q(status="pending"),
                name="suggestions_one_pending_per_finding",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_task_display()}: {self.proposed_text[:60]}"
