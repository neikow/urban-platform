# Deploying websites

Each website of the platform (one per association) is its own Docker Compose project,
running the same image with its own database, cache and files. This directory is the
contract between this repository and whatever deploys it: the deployment agent driven by
the control plane, or someone installing a website by hand.

## The image

Built by `.github/workflows/release.yml` and published on GitHub's registry:

| Image | Tags |
|---|---|
| `ghcr.io/neikow/urban-platform` | `saas`, `saas-<commit>` for each push to `saas`; `1.2.0`, `1.2`, `latest` for each `v1.2.0` tag |
| `ghcr.io/neikow/urban-platform-nginx` | the same tags |
| `ghcr.io/neikow/urban-platform-agent` | the same tags: the [deployment agent](../agent/README.md) |

`/healthz/` answers `{"status": "ok", "version": "<APP_VERSION>"}`: `1.2.0` for a tagged
release, `saas-<commit>` for a build of the branch. A deployment is done when it reports
the version just deployed.

`python manage.py tenant_stats` prints the website's figures as JSON, counts only
(`{"pages": 12, "users": 40}`): the agent reports them to the control plane.

Images are built for `linux/amd64`.

## Running a website

Normally the [agent](../agent/README.md) does all of this, as the control plane asks. By
hand:

[`tenant/compose.yml`](tenant/compose.yml) is the whole website: the app (`web`), the
Celery `worker` (which also runs the scheduler), `nginx`, Postgres (`db`), Redis
(`cache`), and one-shot jobs that run at every `up`: `volumes` (ownership),
`static` (`collectstatic`) and `migrator` (`migrate`, then `bootstrap_tenant`).

```sh
docker network create urban-edge          # once per host, shared with the edge proxy
docker compose -p "$TENANT_SLUG" -f tenant/compose.yml --env-file .env up -d
```

Upgrading is the same command with a new `IMAGE_TAG`: the migrator migrates and
bootstraps again before the app restarts. Expect about 600 MB of memory per website at rest.

### Variables

[`tenant/.env.example`](tenant/.env.example) lists them. Required:

| Variable | |
|---|---|
| `TENANT_SLUG` | Compose project and router name: lowercase letters, digits, dashes. Unique per host |
| `TENANT_HOSTNAME` | Public hostname. `BASE_URL`, `ALLOWED_HOSTS` and the CSRF origins derive from it |
| `IMAGE_TAG` | Release to run |
| `SECRET_KEY`, `DB_PASSWORD` | Generated once for the website, never changed |

The website itself (applied by `bootstrap_tenant` at every deployment, see
`core/tenant.py`):

| Variable | |
|---|---|
| `WEBSITE_NAME` | Default name, until the association sets one in the admin |
| `TENANT_ADMIN_EMAIL` | First administrator, invited by email to choose a password |
| `TENANT_TERRITORY` | INSEE code of the commune or arrondissement; changing it moves the website |
| `TENANT_CONTACT_EMAIL` | Contact address, until the association sets one |

Initial branding, optional. Each value fills its field once, if empty: what the
association changes or removes afterwards stays so, and a new value only fills a field
still empty.

| Variable | |
|---|---|
| `TENANT_TAGLINE` | Tagline under the name |
| `TENANT_PRIMARY_COLOR`, `TENANT_SECONDARY_COLOR` | Theme colours, `#rrggbb` |
| `TENANT_BACKGROUND_COLOR`, `TENANT_TEXT_COLOR` | Background and text, `#rrggbb`; dropped together if their contrast is under 4.5:1 |
| `TENANT_FONT_BODY`, `TENANT_FONT_DISPLAY` | Fonts for text and titles: ids of [`frontend/theme/fonts.json`](../frontend/theme/fonts.json) |
| `TENANT_LOGO_URL`, `TENANT_SIGNUP_IMAGE_URL` | Logo and sign-up photo, downloaded at deployment (http or https, 10 MB at most); retried at the next deployment if unavailable |

Optional: `BREVO_API_KEY`, `DEFAULT_FROM_EMAIL`, `DEFAULT_FROM_NAME` (emails; without a
key, none are sent), `SENTRY_DSN`, `ANALYTICS_SCRIPT_TAG`, `GUNICORN_WORKERS` (2),
`GUNICORN_THREADS` (4), `CELERY_CONCURRENCY` (1), and the edge settings below.

## The edge proxy

Websites do not publish ports by default. Their nginx joins the external `urban-edge`
network (`EDGE_NETWORK`) and carries [Traefik](https://traefik.io) labels: a router named
after `TENANT_SLUG` for `Host(TENANT_HOSTNAME)` on the `websecure` entrypoint
(`EDGE_ENTRYPOINT`), with certificates from the `letsencrypt` resolver
(`EDGE_CERT_RESOLVER`). One Traefik per host serves every website on it.

A host that already has a reverse proxy, with its own certificates, uses the agent's
`external` edge instead (see [`agent/README.md`](../agent/README.md#https-two-ways)): an
override file attaches each website's nginx to the proxy's Docker network as
`<slug>-nginx`, or publishes it on a local port when the proxy runs on the host:

```yaml
services:
  nginx:
    networks:
      proxy:
        aliases: ["aix-nginx"]
networks:
  proxy:
    name: nginx
    external: true
```

## Data

Each project keeps four volumes: `postgres`, `media` (uploads and map tiles), `static`
and `redis`. Back up `postgres` (`pg_dump` in the `db` container) and `media`; the others
are rebuilt. The [agent](../agent/README.md#backups) does it every day when the
control plane turns backups on, on the host and in an S3-compatible bucket. `docker compose -p <slug> down -v` deletes a website and its data.
