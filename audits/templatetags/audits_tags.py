from django import template

from audits.reports import InspectionLog
from audits.reports import inspection_log as build_inspection_log

register = template.Library()


@register.simple_tag
def inspection_log() -> InspectionLog:
    return build_inspection_log()
