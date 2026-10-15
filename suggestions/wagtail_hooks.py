from wagtail import hooks
from wagtail.permissions import register_permission_policy

from audits.views import ReadOnlyPermissionPolicy
from suggestions.models import ProviderCall, Suggestion
from suggestions.views import SuggestionsViewSetGroup

register_permission_policy(Suggestion, ReadOnlyPermissionPolicy(Suggestion))
register_permission_policy(ProviderCall, ReadOnlyPermissionPolicy(ProviderCall))


def register_suggestions_viewsets() -> SuggestionsViewSetGroup:
    return SuggestionsViewSetGroup()


hooks.register("register_admin_viewset", register_suggestions_viewsets)
