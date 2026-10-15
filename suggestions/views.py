from typing import Any

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import URLPattern, path, reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from wagtail.admin import messages
from wagtail.admin.ui.tables import Column, DateColumn, TitleColumn
from wagtail.admin.views.generic import InspectView
from wagtail.admin.viewsets.model import ModelViewSetGroup

from audits.views import ReadOnlyModelViewSet
from suggestions.models import ProviderCall, Suggestion, Task
from suggestions.review import FIELD_FOR_TASK, ReviewError, approve, can_review, reject

PREVIEW_LENGTH = 70


class SuggestionReviewView(InspectView):
    template_name = "suggestions/review.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context: dict[str, Any] = super().get_context_data(**kwargs)
        suggestion: Suggestion = self.object
        page = suggestion.finding.page
        draft = page.get_latest_revision_as_object() if page else None
        field = FIELD_FOR_TASK.get(Task(suggestion.task))
        context.update(
            suggestion=suggestion,
            page=page,
            current_text=getattr(draft, field, "") if draft and field else "",
            is_pending=suggestion.status == Suggestion.Status.PENDING,
            can_review=can_review(suggestion, self.request.user),
            approve_url=reverse("suggestion:approve", args=[suggestion.pk]),
            reject_url=reverse("suggestion:reject", args=[suggestion.pk]),
        )
        return context


@require_POST
def approve_view(request: HttpRequest, pk: int) -> HttpResponse:
    suggestion = _get_suggestion(pk)
    try:
        approve(suggestion, request.user)
    except ReviewError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request,
            _("Saved as a draft. Review and publish it from the page editor."),
            buttons=[
                messages.button(
                    reverse(
                        "wagtailadmin_pages:edit", args=[suggestion.finding.page_id]
                    ),
                    _("Edit page"),
                )
            ],
        )
    return redirect("suggestion:inspect", pk=pk)


@require_POST
def reject_view(request: HttpRequest, pk: int) -> HttpResponse:
    suggestion = _get_suggestion(pk)
    try:
        reject(suggestion, request.user, request.POST.get("note", ""))
    except ReviewError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, _("Suggestion rejected."))
    return redirect("suggestion:inspect", pk=pk)


def _get_suggestion(pk: int) -> Suggestion:
    suggestion: Suggestion = get_object_or_404(
        Suggestion.objects.select_related("finding__page"), pk=pk
    )
    return suggestion


def _preview(text: str) -> str:
    return text if len(text) <= PREVIEW_LENGTH else f"{text[: PREVIEW_LENGTH - 1]}…"


class SuggestionViewSet(ReadOnlyModelViewSet):
    model = Suggestion
    icon = "edit"
    menu_label = _("Suggestions")
    inspect_view_class = SuggestionReviewView
    ordering = ["-created_at"]
    list_filter = ["status", "task"]
    inspect_view_fields = ["task", "status", "proposed_text", "finding", "call"]
    list_display = [
        TitleColumn(
            "proposed_text",
            label=_("Proposed text"),
            url_name="suggestion:inspect",
            accessor=lambda suggestion: _preview(suggestion.proposed_text),
        ),
        Column("task", label=_("Task"), accessor="get_task_display"),
        Column("finding", label=_("Page"), accessor="finding.page"),
        Column("status", label=_("Status"), accessor="get_status_display"),
        DateColumn("created_at", label=_("Created")),
    ]

    def get_urlpatterns(self) -> list[URLPattern]:
        return [
            *super().get_urlpatterns(),
            path("approve/<int:pk>/", approve_view, name="approve"),
            path("reject/<int:pk>/", reject_view, name="reject"),
        ]


class ProviderCallViewSet(ReadOnlyModelViewSet):
    model = ProviderCall
    icon = "history"
    menu_label = _("Model calls")
    ordering = ["-created_at"]
    list_filter = ["task", "provider"]
    inspect_view_fields = [
        "task",
        "provider",
        "model_name",
        "prompt",
        "response",
        "error",
        "requested_by",
        "created_at",
    ]
    list_display = [
        TitleColumn("__str__", label=_("Call"), url_name="providercall:inspect"),
        Column("model_name", label=_("Model")),
        Column("error", label=_("Error")),
        DateColumn("created_at", label=_("Created")),
    ]


class SuggestionsViewSetGroup(ModelViewSetGroup):
    items = (SuggestionViewSet, ProviderCallViewSet)
    menu_label = _("Suggestions")
    menu_icon = "edit"
    menu_order = 260
