import os
import sys
import urllib.error
import urllib.request

HEALTH_URL = "http://127.0.0.1:8000/healthz/"
TIMEOUT_SECONDS = 4


def main() -> int:
    host = os.environ.get("ALLOWED_HOSTS", "localhost").split(",")[0].strip()
    request = urllib.request.Request(HEALTH_URL, headers={"Host": host})
    try:
        # S310 is safe to ignore: the URL is the fixed constant above.
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return 0 if response.status == 200 else 1
    except urllib.error.URLError, TimeoutError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
