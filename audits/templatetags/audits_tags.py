from django import template

from audits.reports import InspectionLog, InspectionStatus
from audits.reports import inspection_log as build_inspection_log
from audits.reports import inspection_status as build_inspection_status

register = template.Library()


@register.simple_tag
def inspection_log() -> InspectionLog:
    return build_inspection_log()


@register.simple_tag
def inspection_status() -> InspectionStatus:
    return build_inspection_status()
