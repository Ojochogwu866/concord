# Concord

I built Concord, a bilingual (English and French) Wagtail site that audits itself. Every night it inspects each published page for missing translations, broken links and redirects, SEO gaps and accessibility problems, and it shows what it finds on the home page and in the Wagtail admin. Where a fix can be drafted, it drafts one for an editor to approve.

![The home page: a large headline, "This site checks its own work", beside an example brief marked up with numbered findings](docs/images/home.png)

Editors work from a findings report in the Wagtail admin that links each problem straight to the page that needs fixing:

![The Site health findings report in the Wagtail admin, listing an open missing-translation error](docs/images/admin-findings.png)

## Why I built it

Multilingual sites drift. A page gets updated in English and the French version quietly falls behind, a slug changes and old links break, an image goes up without alt text. Nobody notices until a reader does. I wanted a site that notices first: one that treats its own health as content, checks it continuously, and hands editors a short list of things to fix rather than a dashboard to interpret.

## What it does

- **Bilingual by design.** English and French with wagtail-localize, `/en/` and `/fr/` URLs, a language switcher that falls back to the home page when a translation is missing, `hreflang` alternates for real translations only, and every interface string translated.
- **Audits itself.** `run_audits` renders every live page and runs translation, accessibility, SEO and redirect checks. Findings persist across runs and resolve themselves once fixed.
- **Checks every link.** `check_links` checks each link on each page and reports one only after three failures in a row, so a flaky server never creates noise.
- **Drafts fixes, never publishes them.** Suggested SEO titles, meta descriptions and translation drafts go to an editor for review, and approving one creates a draft, not a published change.
- **Keeps old URLs working.** Renaming a page creates a permanent redirect, and the audit watches redirects for chains, loops and dead ends.
- **Accessible.** Every public page is checked against WCAG 2.2 AA with axe-core at phone, tablet and desktop widths in both languages, on every build.

## Run it locally

You need Docker. From the repository root:

```bash
docker compose up
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo_content
docker compose exec web python manage.py createsuperuser
```

Open http://localhost:8000 for the site and http://localhost:8000/admin/ for the admin. Then run an audit and a link check:

```bash
docker compose exec web python manage.py run_audits
docker compose exec web python manage.py check_links
```

`seed_demo_content` creates the home page, the briefs index and three briefs, two of them translated into French. I left the third in English on purpose, so the audit always has a real gap to show. It is safe to run again.

## How it works

The project has three apps with clear boundaries: `briefs` holds the content, `audits` finds problems, and `suggestions` drafts fixes for people to review. Removing `suggestions` leaves the rest untouched.

A check is a small function that registers itself and returns findings, so adding one never touches the runner. Page checks receive a rendered page with its HTML parsed once and shared by every check; site checks, like the redirect check, look at the whole site. The runner renders pages through Django's full request stack, so it inspects exactly what visitors get, then saves everything in bulk.

| Code | Severity | What it means |
|---|---|---|
| `i18n.missing_translation` | Error | No published translation of the page in another site language |
| `i18n.stale_translation` | Warning | The translation was last published before its source page |
| `a11y.heading_skip` | Warning | A heading jumps a level, for example h2 to h4 |
| `a11y.img_alt` | Error | An image has no alt attribute |
| `a11y.empty_link` | Error | A link has no text a screen reader can announce |
| `a11y.label` | Error | A form field has no label |
| `a11y.lang` | Error | `<html lang>` does not match the page's language |
| `seo.long_title` | Warning | `<title>` is longer than 60 characters |
| `seo.missing_description` | Warning | No meta description |
| `seo.long_description` | Warning | Meta description is longer than 160 characters |
| `seo.missing_canonical` | Warning | No canonical link |
| `seo.missing_hreflang` | Warning | A published translation is not declared with `hreflang`, or there is no `x-default` |
| `seo.h1_count` | Error | The page does not have exactly one `<h1>` |
| `link.broken` | Error | A link failed three checks in a row: 404, 410, 5xx, a timeout or a connection error |
| `redirect.chain` | Warning | A redirect lands on another redirect |
| `redirect.loop` | Error | Redirects that never reach a page |
| `redirect.broken_target` | Error | A redirect with no target, to an unpublished page, or to a path that errors |

## Decisions I made

- **A finding is a problem, not an event.** Each finding stays open while the problem keeps appearing and resolves on the first run where it does not. A partial unique index stops the same open problem being recorded twice, and each kind of run only resolves the findings it raised, so a page audit can never close a broken link.
- **A page that fails to render is not a clean page.** If one page errors, the run records it and moves on, and that page's findings stay open instead of being marked fixed.
- **Three strikes for links.** A 404, 410, 5xx or network error counts as a failure; 401, 403 and 429 usually mean bot protection or rate limiting, so they count as inconclusive. The checker times out after 10 seconds, retries once, sends at most one request per second to any host from a bounded worker pool, follows at most five redirects, caps how much it downloads, and refuses requests to private, loopback and link-local addresses at every hop.
- **People approve, the model drafts.** Suggestions are checked against the same length limits the audit uses, approving writes a draft built on the page's latest revision so unpublished edits survive, and every model call is logged with its prompt, response and requester. Suggestions stay off unless a provider is configured, so nothing is called or billed by accident.
- **Translations publish immediately.** wagtail-localize defers publishing to the end of the transaction, by which time the queued revision is stale and resets the parent page's child count. I publish each seeded translation straight away so French pages are always routable.
- **Schema changes expand, then contract.** `reading_time` arrives as a nullable column, then a separate, idempotent migration backfills it, so it is safe on a live table and both steps roll back cleanly.

## Suggestions

`suggest_fixes` asks the configured provider for a shorter SEO title or a missing meta description and stores each answer as a pending suggestion. Under **Suggestions** in the admin, an editor compares the current and proposed text, then approves or rejects it. Approving needs permission to edit that page and saves the text into a new draft; nothing is published until an editor publishes the page. For missing translations, the same provider sits behind wagtail-localize's machine-translation button, so drafts appear in the normal translation editor.

Every call is logged under **Suggestions → Model calls**. Development and tests use an offline provider that returns clearly marked placeholder text, and production keeps suggestions off until `SUGGESTIONS_PROVIDER` is set.

```bash
docker compose exec web python manage.py suggest_fixes --limit 10
```

## Migrations and rollback

Every migration is reversible, and CI runs them forward, backward and forward again on PostgreSQL 18 with seeded content.

| App | Migration | Change | Why it is safe | Rollback |
|---|---|---|---|---|
| briefs | `0001_initial` | Pages and topics | New tables only | `migrate briefs zero` |
| briefs | `0002_home_landing_page` | Landing page fields | New columns have defaults; the removed intro was unused | `migrate briefs 0001` |
| briefs | `0003_home_inspection_log_block` | Home page block types | Changes only StreamField block definitions | `migrate briefs 0002` |
| briefs | `0004_brief_reading_time` | Add `reading_time` | Nullable column, so no table rewrite and no backfill at add time | `migrate briefs 0003` removes the column |
| briefs | `0005_backfill_reading_time` | Compute reading time from word count | Idempotent; carries a frozen copy of the formula | Reverse is a no-op; the data is harmless left in place |
| audits | `0001`–`0004` | Runs, findings, constraint fix, labels, link checks | New tables and a partial unique index | `migrate audits zero` |
| suggestions | `0001_initial` | Suggestions and model calls | New tables only | `migrate suggestions zero` |

```bash
python manage.py makemigrations --check --dry-run   # fails if a migration is missing
python manage.py sqlmigrate briefs 0004             # read the SQL before it touches production
python manage.py migrate                            # forward
python manage.py migrate briefs 0003                # back
python manage.py migrate                            # forward again
```

The same commands run locally, in CI and in production. I take a `pg_dump` before running migrations in production.

## Checks and tests

```bash
pytest                                              # unit and integration tests
ruff check . && ruff format --check .               # lint and format
mypy .                                              # strict type check
docker compose --profile prod up -d --build web-prod
npx playwright test                                 # axe-core and keyboard checks
```

Tests never touch the network: every HTTP request is mocked with respx. The Playwright suite runs against the production image on port 8001, because Django's debug pages replace the real error templates in development. Set `BASE_URL` to run it against a deployed site.

## Deploying

I deploy the Docker image on Coolify, with the database on Neon and uploaded images on Cloudflare R2. The image serves the site with gunicorn, serves static files with WhiteNoise, and reports its health at `/healthz/`, so a deploy that cannot reach its database never takes traffic.

| Variable | Example |
|---|---|
| `SECRET_KEY` | A long random string |
| `DATABASE_URL` | `postgres://user:password@host:5432/concord` |
| `ALLOWED_HOSTS` | `concord.example.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://concord.example.com` |
| `WAGTAILADMIN_BASE_URL` | `https://concord.example.com` (also sets the Wagtail site's address) |
| `R2_BUCKET_NAME`, `R2_BUCKET_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | Cloudflare R2 bucket for uploaded images |
| `R2_PUBLIC_URL` | Optional public domain for the bucket; without it, image URLs are signed |
| `SUGGESTIONS_PROVIDER` | Optional dotted path to a suggestion provider; leave unset to keep suggestions off |

On the host:

- Build from the Dockerfile and expose port 8000.
- Run `python manage.py migrate --noinput && python manage.py seed_demo_content` before each deployment starts.
- Schedule `python manage.py run_audits` and `python manage.py check_links` to run nightly.
- Use Neon's pooled connection string; production settings already disable the server-side cursors it does not support.
- Point a proxied Cloudflare DNS record at the host, with SSL mode Full (strict).

GitHub Actions runs lint, types, migrations, tests and the accessibility suite on every push and pull request. On `main`, it calls the host's deploy webhook once both pass, if the `DEPLOY_WEBHOOK_URL` and `DEPLOY_TOKEN` secrets are set. Setting the `PUBLIC_SITE_URL` variable runs the accessibility suite against the live site every night.

## What's next

- A Claude provider behind the suggestions interface. The review flow and translator hook are built and tested; connecting a model is a small class and one setting.
- Alt-text suggestions from a vision model
- Meaning-drift detection: comparing what the English and French versions actually say, not just when each was published
- A dashboard panel on the admin home page, and a nightly email digest of new findings
