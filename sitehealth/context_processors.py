from django.conf import settings
from django.http import HttpRequest


def site_credits(request: HttpRequest) -> dict[str, str]:
    return {"designer_profile_url": settings.DESIGNER_PROFILE_URL}
