from typing import Any

import django_filters
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.db.models import Case, IntegerField, QuerySet, Value, When
from django.urls import URLPattern, path, reverse
from django.utils.translation import gettext_lazy as _
from wagtail.admin.filters import LocaleFilter, WagtailFilterSet
from wagtail.admin.ui.tables import (
    Column,
    DateColumn,
    LocaleColumn,
    StatusFlagColumn,
    TitleColumn,
)
from wagtail.admin.views.generic import IndexView
from wagtail.admin.viewsets.model import ModelViewSet, ModelViewSetGroup
from wagtail.permission_policies import ModelPermissionPolicy

from audits.models import AuditRun, Finding

READ_ONLY_ACTIONS = {"view"}


class ReadOnlyPermissionPolicy(ModelPermissionPolicy):
    # Findings and runs are written only by run_audits, never by hand.
    def user_has_permission(
        self, user: AbstractBaseUser | AnonymousUser, action: str
    ) -> bool:
        return action in READ_ONLY_ACTIONS and bool(
            super().user_has_permission(user, action)
        )


class FindingFilterSet(WagtailFilterSet):
    status = django_filters.ChoiceFilter(
        label=_("Status"),
        choices=[("open", _("Open")), ("resolved", _("Resolved"))],
        method="filter_status",
        empty_label=_("All"),
    )
    category = django_filters.ChoiceFilter(
        label=_("Category"),
        choices=[
            ("i18n.", _("Translation")),
            ("a11y.", _("Accessibility")),
            ("redirect.", _("Redirects")),
            ("seo.", _("SEO")),
            ("link.", _("Links")),
        ],
        field_name="code",
        lookup_expr="startswith",
        empty_label=_("All"),
    )
    locale = LocaleFilter(
        label=_("Language"),
        choices=settings.WAGTAIL_CONTENT_LANGUAGES,
        empty_label=_("All"),
    )

    class Meta:
        model = Finding
        fields = ["severity", "code"]

    def filter_status(
        self, queryset: QuerySet[Finding], name: str, value: str
    ) -> QuerySet[Finding]:
        return queryset.filter(resolved_at__isnull=value == "open")


class PageColumn(Column):
    cell_template_name = "audits/tables/page_cell.html"

    def get_cell_context_data(
        self, instance: Finding, parent_context: dict[str, Any]
    ) -> dict[str, Any]:
        context: dict[str, Any] = super().get_cell_context_data(
            instance, parent_context
        )
        if instance.page_id:
            context["edit_url"] = reverse(
                "wagtailadmin_pages:edit", args=[instance.page_id]
            )
        return context


class FindingIndexView(IndexView):
    def get_base_queryset(self) -> QuerySet[Finding]:
        queryset: QuerySet[Finding] = super().get_base_queryset()
        # PostgreSQL sorts NULL last, so rank open findings to list them first.
        return queryset.select_related("page", "locale").annotate(
            open_rank=Case(
                When(resolved_at__isnull=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        )


class ReadOnlyModelViewSet(ModelViewSet):
    copy_view_enabled = False
    inspect_view_enabled = True

    def get_urlpatterns(self) -> list[URLPattern]:
        return [
            path("", self.index_view, name="index"),
            path("results/", self.index_results_view, name="index_results"),
            path(
                f"inspect/<{self.pk_path_converter}:pk>/",
                self.inspect_view,
                name="inspect",
            ),
        ]


class FindingViewSet(ReadOnlyModelViewSet):
    model = Finding
    icon = "warning"
    menu_label = _("Findings")
    index_view_class = FindingIndexView
    filterset_class = FindingFilterSet
    search_fields = ["code", "message", "url"]
    ordering = ["open_rank", "-last_seen_at"]
    inspect_view_fields = [
        "code",
        "severity",
        "message",
        "page",
        "locale",
        "url",
        "first_seen_at",
        "last_seen_at",
        "resolved_at",
        "run",
    ]
    list_display = [
        TitleColumn(
            "code", label=_("Finding"), sort_key="code", url_name="finding:inspect"
        ),
        Column(
            "severity",
            label=_("Severity"),
            accessor="get_severity_display",
            sort_key="severity",
        ),
        PageColumn("page", label=_("Page")),
        LocaleColumn(label=_("Language")),
        StatusFlagColumn("is_open", label=_("Status"), true_label=_("Open")),
        DateColumn("last_seen_at", label=_("Last seen")),
    ]


class AuditRunViewSet(ReadOnlyModelViewSet):
    model = AuditRun
    icon = "history"
    menu_label = _("Runs")
    ordering = ["-started_at"]
    list_filter = ["status"]
    list_display = [
        TitleColumn("__str__", label=_("Run"), url_name="auditrun:inspect"),
        Column("status", label=_("Status"), accessor="get_status_display"),
        Column("pages_inspected", label=_("Pages inspected")),
        Column("pages_failed", label=_("Pages failed")),
        DateColumn("finished_at", label=_("Finished")),
    ]


class SiteHealthViewSetGroup(ModelViewSetGroup):
    items = (FindingViewSet, AuditRunViewSet)
    menu_label = _("Site health")
    menu_icon = "warning"
    menu_order = 250
