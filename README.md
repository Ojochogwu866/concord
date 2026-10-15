# Concord

I built a bilingual (English and French) Wagtail site that audits itself: it inspects every published page for missing translations, broken links and redirects, SEO gaps and accessibility problems, and lists what it finds on the home page and in the Wagtail admin. It is a test build I made to learn the Wagtail stack, not production experience.

![The home page: a large headline, "This site checks its own work", beside an example brief marked up with numbered findings](docs/images/home.png)

Editors work from a read-only findings report in the Wagtail admin, which links each problem straight to the page that needs fixing:

![The Site health findings report in the Wagtail admin, listing an open missing-translation error](docs/images/admin-findings.png)

## Run it locally

You need Docker. From the repository root:

```bash
docker compose up
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo_content
docker compose exec web python manage.py createsuperuser
```

Then open http://localhost:8000 for the site and http://localhost:8000/admin/ for the admin. Run an audit and a link check with:

```bash
docker compose exec web python manage.py run_audits
docker compose exec web python manage.py check_links
```

`seed_demo_content` creates the home page, the briefs index and three briefs, two of them translated into French. It is safe to run again. The third brief is left in English on purpose, so the audit always has a real gap to report.

## What is built, and what is not yet

Built:

- English and French site with wagtail-localize, `/en/` and `/fr/` URLs, a language switcher, `hreflang` alternates, and French translations of every interface string
- Brief, briefs index and landing pages with a StreamField content model; figures require alt text or an explicit "decorative" choice
- An audit engine (`run_audits`) with a check registry, persistent findings that resolve themselves once fixed, and handling for pages that fail to render
- Checks for missing and out-of-date translations, five accessibility rules, six SEO rules, and redirect chains, loops and broken targets
- A link checker (`check_links`) that reports a link only after three failed checks in a row, with timeouts, retries, a per-host rate limit, a bounded worker pool and protection against requests to private addresses
- Automatic redirects when a page's slug changes
- An inspection log on the home page and a read-only findings report in the Wagtail admin
- Two safe migrations for `reading_time`: add the column, then backfill it
- Playwright and axe-core checks for WCAG 2.2 AA at 360, 768 and 1280 px, in both languages
- A multi-stage Docker image and GitHub Actions for CI, deployment and a nightly accessibility run

Not built yet:

- AI-drafted fixes that editors approve, starting with translation drafts
- A dashboard panel on the admin home page, and a nightly email digest

## How it works

The project has two apps that are kept apart. `briefs` holds the content pages and `audits` holds the scan results.

A check is a small function that registers itself and returns findings. Page checks receive one rendered page, with its HTML parsed once and shared by every check. Site checks, such as the redirect check, look at the whole site. `run_audits` renders every live page through Django's full request stack, so it inspects exactly what visitors get, then saves the results in bulk. A finding stays open while the problem keeps appearing and is marked resolved on the first run where it does not.

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
| `link.broken` | Error | A link failed three checks in a row: 404, 410, 5xx, a timeout or a connection error. 401, 403 and 429 count as inconclusive. |
| `redirect.chain` | Warning | A redirect lands on another redirect |
| `redirect.loop` | Error | Redirects that never reach a page |
| `redirect.broken_target` | Error | A redirect with no target, to an unpublished page, or to a path that errors |

## Migrations and rollback

Every migration is reversible, and CI runs them forward, backward and forward again on PostgreSQL with seeded content.

| App | Migration | Change | Why it is safe | Rollback |
|---|---|---|---|---|
| briefs | `0001_initial` | Pages and topics | New tables only | `migrate briefs zero` |
| briefs | `0002_home_landing_page` | Landing page fields | New columns have defaults; the removed intro was unused | `migrate briefs 0001` |
| briefs | `0003_home_inspection_log_block` | Home page block types | Changes only StreamField block definitions | `migrate briefs 0002` |
| briefs | `0004_brief_reading_time` | Add `reading_time` | Nullable column, so no table rewrite and no backfill at add time | `migrate briefs 0003` removes the column |
| briefs | `0005_backfill_reading_time` | Compute reading time from word count | Idempotent; carries a frozen copy of the formula | Reverse is a no-op; the data is harmless left in place |
| audits | `0001`–`0004` | Runs, findings, constraint fix, labels, link checks | New tables and a partial unique index | `migrate audits zero` |

A rename or type change should follow expand and contract: add the new column, backfill it, move the code over, and drop the old column in a later release.

```bash
python manage.py makemigrations --check --dry-run   # fails if a migration is missing
python manage.py sqlmigrate briefs 0004             # read the SQL before it touches production
python manage.py migrate                            # forward
python manage.py migrate briefs 0003                # back
python manage.py migrate                            # forward again
```

The same commands run locally, in CI and in production. Take a `pg_dump` before running migrations in production.

## Checks and tests

```bash
pytest                                              # unit and integration tests
ruff check . && ruff format --check .               # lint and format
mypy .                                              # strict type check
docker compose --profile prod up -d --build web-prod
npx playwright test                                 # axe-core and keyboard checks
```

The Playwright suite runs against the production image on port 8001, because Django's debug pages replace the real error templates in development. Set `BASE_URL` to run it against a deployed site.

## Deploying

The production image serves the site with gunicorn and serves static files with WhiteNoise. It needs these environment variables:

| Variable | Example |
|---|---|
| `SECRET_KEY` | A long random string |
| `DATABASE_URL` | `postgres://user:password@host:5432/sitehealth` |
| `ALLOWED_HOSTS` | `health.example.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://health.example.com` |
| `WAGTAILADMIN_BASE_URL` | `https://health.example.com` (also sets the Wagtail site's address) |
| `R2_BUCKET_NAME`, `R2_BUCKET_URL`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | Cloudflare R2 bucket for uploaded images |
| `R2_PUBLIC_URL` | Optional public domain for the bucket; without it, image URLs are signed |

On the host (I use Coolify), build from the Dockerfile and expose port 8000. Then:

- Run `python manage.py migrate --noinput && python manage.py seed_demo_content` before each deployment starts.
- Schedule `python manage.py run_audits` and `python manage.py check_links` to run nightly.
- Set `DATABASE_URL` to Neon's pooled connection string; production settings already disable the server-side cursors it does not support.
- Set the `R2_*` variables to store uploaded images in Cloudflare R2. Without them, uploads go to the container's filesystem and are lost on redeploy.
- Point a Cloudflare DNS record at the host, proxied, with SSL mode Full (strict).

GitHub Actions runs lint, types, migrations, tests and the accessibility suite on every push and pull request. On `main`, it calls the host's deploy webhook once both pass, if the `DEPLOY_WEBHOOK_URL` and `DEPLOY_TOKEN` secrets are set. Set the `PUBLIC_SITE_URL` variable to run the accessibility suite against the live site every night.
# concord
