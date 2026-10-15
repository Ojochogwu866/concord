HOME_HEADING = "This site checks its own work."

HOME_LEAD = (
    "A bilingual Wagtail site that inspects every page it publishes for missing "
    "translations, broken redirects, dead links and accessibility problems, then "
    "hands editors a list to fix."
)

INSPECTION_LOG_NOTE = (
    "The audit renders each published page and records what it finds. "
    "Problems that get fixed drop off on the next run."
)

LATEST_BRIEFS_NOTE = (
    "The content the inspection runs against. Two are translated into French; "
    "one is left untranslated on purpose."
)

HOME_BODY = [
    {
        "type": "inspection_log",
        "value": {
            "heading": "Inspection log",
            "note": INSPECTION_LOG_NOTE,
        },
    },
    {
        "type": "latest_briefs",
        "value": {
            "heading": "Briefs",
            "note": LATEST_BRIEFS_NOTE,
        },
    },
]

# French typography puts a narrow no-break space (U+202F) before ; : ? and !
FRENCH_TRANSLATIONS = {
    "Concord": "Concord",
    "home": "accueil",
    HOME_HEADING: "Ce site vérifie son propre travail.",
    HOME_LEAD: (
        "Un site Wagtail bilingue qui inspecte chaque page publiée à la recherche "
        "de traductions manquantes, de redirections cassées, de liens morts et de "
        "problèmes d’accessibilité, puis remet aux éditeurs une liste de "
        "corrections."
    ),
    "Inspection log": "Journal d’inspection",
    INSPECTION_LOG_NOTE: (
        "L’audit affiche chaque page publiée et consigne ce qu’il trouve. "
        "Les problèmes corrigés disparaissent au passage suivant."
    ),
    "Briefs": "Notes",
    "briefs": "notes",
    LATEST_BRIEFS_NOTE: (
        "Le contenu que l’inspection passe en revue. Deux notes sont traduites "
        "en français ; la troisième est volontairement laissée en anglais."
    ),
}
