import datetime

AUTHOR = "Dickson Ojochogwu"

DEMO_TOPICS = [
    {"name": "Accessibility", "slug": "accessibility"},
    {"name": "Multilingual sites", "slug": "multilingual-sites"},
    {"name": "Maintenance", "slug": "maintenance"},
]

DEMO_BRIEFS = [
    {
        "title": "What changed in WCAG 2.2",
        "slug": "what-changed-in-wcag-2-2",
        "published_date": datetime.date(2026, 9, 8),
        "topics": ["accessibility"],
        "summary": (
            "WCAG 2.2 adds nine success criteria and retires one. Most of the "
            "changes protect people who use a keyboard, a pointer with limited "
            "precision, or who find memory tasks hard."
        ),
        "body": [
            {
                "type": "paragraph",
                "value": (
                    "<p>The W3C published WCAG 2.2 as a Recommendation on 5 October "
                    "2023. It keeps everything in WCAG 2.1, adds nine success "
                    "criteria, and removes 4.1.1 Parsing, which modern browsers "
                    "made obsolete.</p>"
                ),
            },
            {
                "type": "heading",
                "value": {"text": "The new criteria at level AA", "level": "h2"},
            },
            {
                "type": "paragraph",
                "value": (
                    "<ul><li><b>Focus Not Obscured (Minimum):</b> a focused element "
                    "must not be completely hidden by sticky headers or banners."
                    "</li><li><b>Dragging Movements:</b> anything done by dragging "
                    "must also work with a single pointer.</li><li><b>Target Size "
                    "(Minimum):</b> targets need to be at least 24 by 24 CSS pixels, "
                    "or spaced so they do not overlap.</li><li><b>Accessible "
                    "Authentication (Minimum):</b> signing in must not depend on "
                    "remembering or transcribing something.</li></ul>"
                ),
            },
            {
                "type": "quote",
                "value": {
                    "quote": (
                        "Following these guidelines will make content more "
                        "accessible to a wider range of people with disabilities."
                    ),
                    "attribution": "W3C, Web Content Accessibility Guidelines 2.2",
                },
            },
            {
                "type": "heading",
                "value": {"text": "What it means for this site", "level": "h2"},
            },
            {
                "type": "paragraph",
                "value": (
                    "<p>Every public page here is checked against WCAG 2.2 AA with "
                    "axe-core on each build, at phone, tablet and desktop widths. "
                    "The full list of changes is in "
                    '<a href="https://www.w3.org/WAI/standards-guidelines/wcag/'
                    'new-in-22/">What’s New in WCAG 2.2</a>.</p>'
                ),
            },
        ],
    },
    {
        "title": "How hreflang tells search engines which language to show",
        "slug": "how-hreflang-works",
        "published_date": datetime.date(2026, 8, 25),
        "topics": ["multilingual-sites"],
        "summary": (
            "A bilingual site publishes the same content twice. hreflang "
            "annotations tell search engines the pages belong together, so each "
            "reader lands on their own language."
        ),
        "body": [
            {
                "type": "paragraph",
                "value": (
                    "<p>Without hreflang, a search engine sees an English page and a "
                    "French page with the same structure. It may show readers the "
                    "wrong one, or treat the pair as duplicates.</p>"
                ),
            },
            {
                "type": "heading",
                "value": {"text": "Three rules that are easy to break", "level": "h2"},
            },
            {
                "type": "paragraph",
                "value": (
                    "<ul><li><b>Annotations must be reciprocal.</b> If the English "
                    "page points to the French one, the French page must point "
                    "back.</li><li><b>Only point to pages that exist.</b> An "
                    "alternate that returns an error is ignored.</li><li><b>Name a "
                    "default.</b> The x-default value says which page to show when "
                    "no language matches the reader.</li></ul>"
                ),
            },
            {
                "type": "heading",
                "value": {"text": "How this site does it", "level": "h2"},
            },
            {
                "type": "paragraph",
                "value": (
                    "<p>Each page lists alternates only for translations that are "
                    "published, and uses the English page as the default. When a "
                    "brief has no French version, the French alternate is left out "
                    "rather than pointing somewhere else. Google documents the "
                    'format in <a href="https://developers.google.com/search/docs/'
                    'specialty/international/localized-versions">Tell Google about '
                    "localized versions of your page</a>.</p>"
                ),
            },
        ],
    },
    {
        "title": "Link rot: why links break and how to catch them",
        "slug": "link-rot",
        "published_date": datetime.date(2026, 9, 30),
        "topics": ["maintenance"],
        "summary": (
            "Pages move, sites close and domains lapse. A link that worked when it "
            "was published can fail years later without anyone noticing."
        ),
        "body": [
            {
                "type": "paragraph",
                "value": (
                    "<p>In 2024, Pew Research Center found that 38% of webpages that "
                    "existed in 2013 were no longer accessible a decade later, and "
                    "that 23% of news pages contained at least one broken link. "
                    'Read the <a href="https://www.pewresearch.org/data-labs/2024/'
                    '05/17/when-online-content-disappears/">full study</a>.</p>'
                ),
            },
            {
                "type": "heading",
                "value": {"text": "Why one failed check is not enough", "level": "h2"},
            },
            {
                "type": "paragraph",
                "value": (
                    "<p>Servers go down for minutes at a time. A checker that "
                    "reports every failure buries editors in noise, so this site "
                    "records each result and raises a finding only after three "
                    "failures in a row.</p>"
                ),
            },
            {
                "type": "heading",
                "value": {"text": "Redirects are part of the fix", "level": "h2"},
            },
            {
                "type": "paragraph",
                "value": (
                    "<p>When a page here changes its address, Wagtail keeps a "
                    "redirect from the old one. The audit then checks those "
                    "redirects for chains, loops and dead ends.</p>"
                ),
            },
        ],
    },
]

TRANSLATED_BRIEF_SLUGS = ["what-changed-in-wcag-2-2", "how-hreflang-works"]

FRENCH_DEMO_TRANSLATIONS = {
    AUTHOR: AUTHOR,
    "Accessibility": "Accessibilité",
    "accessibility": "accessibilite",
    "Multilingual sites": "Sites multilingues",
    "multilingual-sites": "sites-multilingues",
    "Maintenance": "Maintenance",
    "maintenance": "maintenance",
    "What changed in WCAG 2.2": "Ce qui change avec les WCAG 2.2",
    "what-changed-in-wcag-2-2": "ce-qui-change-avec-wcag-2-2",
    (
        "WCAG 2.2 adds nine success criteria and retires one. Most of the changes "
        "protect people who use a keyboard, a pointer with limited precision, or who "
        "find memory tasks hard."
    ): (
        "Les WCAG 2.2 ajoutent neuf critères de succès et en retirent un. La plupart "
        "des changements protègent les personnes qui naviguent au clavier, utilisent "
        "un pointeur peu précis ou ont du mal avec les tâches de mémorisation."
    ),
    (
        "The W3C published WCAG 2.2 as a Recommendation on 5 October 2023. It keeps "
        "everything in WCAG 2.1, adds nine success criteria, and removes 4.1.1 "
        "Parsing, which modern browsers made obsolete."
    ): (
        "Le W3C a publié les WCAG 2.2 comme Recommandation le 5 octobre 2023. Elles "
        "reprennent l’intégralité des WCAG 2.1, ajoutent neuf critères de succès et "
        "retirent le critère 4.1.1 Analyse syntaxique, devenu inutile avec les "
        "navigateurs modernes."
    ),
    "The new criteria at level AA": "Les nouveaux critères de niveau AA",
    (
        "<b>Focus Not Obscured (Minimum):</b> a focused element must not be "
        "completely hidden by sticky headers or banners."
    ): (
        "<b>Focus non masqué (minimum) :</b> un élément qui a le focus ne doit pas "
        "être entièrement caché par un en-tête ou un bandeau fixe."
    ),
    (
        "<b>Dragging Movements:</b> anything done by dragging must also work with a "
        "single pointer."
    ): (
        "<b>Mouvements de glissement :</b> tout ce qui se fait par glissement doit "
        "aussi fonctionner avec un simple pointeur."
    ),
    (
        "<b>Target Size (Minimum):</b> targets need to be at least 24 by 24 CSS "
        "pixels, or spaced so they do not overlap."
    ): (
        "<b>Taille des cibles (minimum) :</b> les cibles doivent mesurer au moins "
        "24 pixels CSS sur 24, ou être assez espacées pour ne pas se chevaucher."
    ),
    (
        "<b>Accessible Authentication (Minimum):</b> signing in must not depend on "
        "remembering or transcribing something."
    ): (
        "<b>Authentification accessible (minimum) :</b> se connecter ne doit pas "
        "exiger de mémoriser ou de recopier une information."
    ),
    (
        "Following these guidelines will make content more accessible to a wider "
        "range of people with disabilities."
    ): (
        "Suivre ces règles rendra les contenus plus accessibles à un plus grand "
        "nombre de personnes en situation de handicap."
    ),
    "W3C, Web Content Accessibility Guidelines 2.2": (
        "W3C, Règles pour l’accessibilité des contenus Web 2.2"
    ),
    "What it means for this site": "Ce que cela change pour ce site",
    (
        "Every public page here is checked against WCAG 2.2 AA with axe-core on each "
        "build, at phone, tablet and desktop widths. The full list of changes is in "
        '<a id="a1">What’s New in WCAG 2.2</a>.'
    ): (
        "Chaque page publique de ce site est vérifiée selon les WCAG 2.2 AA avec "
        "axe-core à chaque compilation, en largeur téléphone, tablette et ordinateur. "
        "La liste complète des changements figure dans "
        '<a id="a1">What’s New in WCAG 2.2</a> (en anglais).'
    ),
    "How hreflang tells search engines which language to show": (
        "Comment hreflang indique aux moteurs de recherche quelle langue afficher"
    ),
    "how-hreflang-works": "comment-fonctionne-hreflang",
    (
        "A bilingual site publishes the same content twice. hreflang annotations "
        "tell search engines the pages belong together, so each reader lands on "
        "their own language."
    ): (
        "Un site bilingue publie deux fois le même contenu. Les annotations hreflang "
        "indiquent aux moteurs de recherche que ces pages vont ensemble, pour que "
        "chaque lecteur arrive dans sa langue."
    ),
    (
        "Without hreflang, a search engine sees an English page and a French page "
        "with the same structure. It may show readers the wrong one, or treat the "
        "pair as duplicates."
    ): (
        "Sans hreflang, un moteur de recherche voit une page anglaise et une page "
        "française de même structure. Il peut montrer la mauvaise au lecteur, ou "
        "traiter les deux comme des doublons."
    ),
    "Three rules that are easy to break": "Trois règles faciles à enfreindre",
    (
        "<b>Annotations must be reciprocal.</b> If the English page points to the "
        "French one, the French page must point back."
    ): (
        "<b>Les annotations doivent être réciproques.</b> Si la page anglaise pointe "
        "vers la page française, la page française doit pointer en retour."
    ),
    (
        "<b>Only point to pages that exist.</b> An alternate that returns an error "
        "is ignored."
    ): (
        "<b>Ne pointer que vers des pages qui existent.</b> Une variante qui renvoie "
        "une erreur est ignorée."
    ),
    (
        "<b>Name a default.</b> The x-default value says which page to show when no "
        "language matches the reader."
    ): (
        "<b>Désigner une page par défaut.</b> La valeur x-default indique quelle "
        "page afficher quand aucune langue ne correspond au lecteur."
    ),
    "How this site does it": "Comment ce site s’y prend",
    (
        "Each page lists alternates only for translations that are published, and "
        "uses the English page as the default. When a brief has no French version, "
        "the French alternate is left out rather than pointing somewhere else. Google "
        'documents the format in <a id="a1">Tell Google about localized versions of '
        "your page</a>."
    ): (
        "Chaque page ne déclare des variantes que pour les traductions publiées, et "
        "utilise la page anglaise par défaut. Quand une note n’a pas de version "
        "française, la variante française est omise plutôt que de pointer ailleurs. "
        'Google documente le format dans <a id="a1">Indiquer à Google les versions '
        "localisées de votre page</a>."
    ),
}
