from django import template
from django.template import Context

from audits.reports import (
    InspectionLog,
    InspectionStatus,
    latest_completed_run,
    open_finding_count,
)
from audits.reports import inspection_log as build_inspection_log
from sitehealth.request_cache import cached_for_request

register = template.Library()


@register.simple_tag(takes_context=True)
def inspection_status(context: Context) -> InspectionStatus:
    request = context.get("request")
    latest_run = cached_for_request(
        request, "latest_completed_run", latest_completed_run
    )
    open_count = (
        cached_for_request(request, "open_finding_count", open_finding_count)
        if latest_run
        else 0
    )
    return InspectionStatus(latest_run=latest_run, open_count=open_count)


@register.simple_tag(takes_context=True)
def inspection_log(context: Context) -> InspectionLog:
    status = inspection_status(context)
    return build_inspection_log(status.latest_run, status.open_count)
