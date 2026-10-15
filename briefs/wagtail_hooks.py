from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from briefs.models import Topic


class TopicViewSet(SnippetViewSet):
    model = Topic
    icon = "tag"
    list_display = ["name", "slug"]


register_snippet(TopicViewSet)
