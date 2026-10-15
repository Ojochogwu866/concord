from wagtail import hooks
from wagtail.permissions import register_permission_policy

from audits.models import AuditRun, Finding
from audits.views import ReadOnlyPermissionPolicy, SiteHealthViewSetGroup

register_permission_policy(Finding, ReadOnlyPermissionPolicy(Finding))
register_permission_policy(AuditRun, ReadOnlyPermissionPolicy(AuditRun))


def register_site_health_viewsets() -> SiteHealthViewSetGroup:
    return SiteHealthViewSetGroup()


hooks.register("register_admin_viewset", register_site_health_viewsets)
