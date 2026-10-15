HOME_HEADING = "This site checks its own work."

HOME_LEAD = (
    "A bilingual Wagtail site that inspects every page it publishes for missing "
    "translations, broken redirects, dead links and accessibility problems, then "
    "hands editors a list to fix."
)

HOME_BODY = [
    {
        "type": "inspection_log",
        "value": {
            "heading": "Inspection log",
            "note": (
                "The audit renders each published page and records what it finds. "
                "Problems that get fixed drop off on the next run."
            ),
        },
    },
    {
        "type": "latest_briefs",
        "value": {
            "heading": "Briefs",
            "note": (
                "The content the inspection runs against. Two are translated into "
                "French; one is left untranslated on purpose."
            ),
        },
    },
]
