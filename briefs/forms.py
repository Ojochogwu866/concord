from typing import Any

from wagtail.admin.forms import WagtailAdminPageForm


class BriefPageForm(WagtailAdminPageForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        topics = self.fields.get("topics")
        if topics is not None and self.instance.locale_id:
            topics.queryset = topics.queryset.filter(locale_id=self.instance.locale_id)
