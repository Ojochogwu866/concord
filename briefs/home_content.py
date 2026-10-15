HOME_HEADING = "A bilingual Wagtail site that audits itself"

HOME_LEAD = (
    "This site scans its own pages for missing translations, broken redirects, "
    "dead links and accessibility problems, and lists what it finds in the "
    "Wagtail admin so editors can fix them."
)

HOME_BODY = [
    {
        "type": "features",
        "value": {
            "heading": "What it checks",
            "items": [
                {
                    "title": "Translations",
                    "description": (
                        "Every English page has a French version, and no French "
                        "page is older than the English page it was translated from."
                    ),
                    "code": "i18n.*",
                },
                {
                    "title": "Redirects",
                    "description": (
                        "Old URLs still lead somewhere: no redirect chains, no "
                        "loops, and no redirects to pages that no longer exist."
                    ),
                    "code": "redirect.*",
                },
                {
                    "title": "Links",
                    "description": (
                        "Every link on every page still resolves. A link is "
                        "reported only after three failed checks in a row."
                    ),
                    "code": "link.*",
                },
                {
                    "title": "SEO and accessibility",
                    "description": (
                        "Titles, descriptions, heading order, alt text, language "
                        "tags and alternate-language links."
                    ),
                    "code": "seo.*  a11y.*",
                },
            ],
        },
    },
    {
        "type": "steps",
        "value": {
            "heading": "How it works",
            "steps": [
                {
                    "title": "Scan",
                    "description": (
                        "A management command renders each live page and runs "
                        "small, independent checks against it."
                    ),
                    "code": "manage.py run_audits",
                },
                {
                    "title": "Record",
                    "description": (
                        "Each problem is stored as a finding with a code, a "
                        "severity and the page it came from. Problems that "
                        "disappear are marked resolved on the next run."
                    ),
                    "code": "",
                },
                {
                    "title": "Review",
                    "description": (
                        "Editors see open findings in the Wagtail admin, filtered "
                        "by code, severity and language."
                    ),
                    "code": "",
                },
            ],
            "image": None,
        },
    },
    {
        "type": "latest_briefs",
        "value": {
            "heading": "Sample briefs",
            "note": (
                "These briefs are the content the audits run against. Two are "
                "translated into French; one is left untranslated on purpose so "
                "the report always has something to show."
            ),
        },
    },
    {
        "type": "text",
        "value": {
            "heading": "Built with",
            "body": (
                "<p>Wagtail and wagtail-localize on Django, PostgreSQL, Tailwind "
                "CSS, Docker and GitHub Actions. Every public page is checked "
                "against WCAG 2.2 AA with Playwright and axe-core.</p>"
            ),
        },
    },
]
