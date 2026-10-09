# Deployment agent

Runs the platform's websites on one host, as the control plane asks. It runs on the
platform's servers and on associations' own machines alike: it only makes outgoing HTTPS
requests, so the host needs no SSH access and no open port besides the websites' own.

Every few seconds it fetches the desired state from the control plane, deploys what
changed with Docker Compose ([`deploy/`](../deploy/README.md)), and reports back. It is
standard-library Python driving the Docker CLI: short enough to read before installing.

## What it can and cannot do

The agent drives Docker through its socket, which amounts to root access to the host. It
therefore limits what the control plane can ask of it:

- It only runs images under one name (`AGENT_IMAGE`, `ghcr.io/neikow/urban-platform` by
  default, and its own `-agent` image to update itself): the control plane chooses a
  tag, never an image.
- The Compose file comes from that image (`/app/deploy/tenant/compose.yml`), not from the
  control plane.
- Website names, tags and variables are checked before anything reaches Docker; a
  website the control plane leaves out of the desired state is left as it is.
- A website's data is only deleted when the control plane marks it `absent` with
  `purge`. Stopping the agent stops nothing: the websites keep running.

## Installing

Docker Engine with the Compose plugin. Then, with the token the control plane gives for
this host:

```sh
docker run -d --name urban-agent --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v urban-agent:/var/lib/urban-agent \
  -e CONTROL_PLANE_URL=https://control.example.org \
  -e AGENT_TOKEN=<token> \
  ghcr.io/neikow/urban-platform-agent:latest
```

Add `--network <name>` to run the agent on another Docker network, e.g. the one of a reverse
proxy that already runs in Docker. It only needs to reach the control plane.

| Variable | Default | |
|---|---|---|
| `CONTROL_PLANE_URL` | | Required, `https://` |
| `AGENT_TOKEN` | | Required: identifies the host |
| `AGENT_IMAGE` | `ghcr.io/neikow/urban-platform` | The only image websites may run (and its `-nginx`) |
| `AGENT_POLL_SECONDS` | `30` | |
| `AGENT_RETRY_SECONDS` | `300` | Delay before trying a failed deployment again |
| `AGENT_STATS_SECONDS` | `900` | How often the websites' figures are collected |
| `AGENT_STATE_DIR` | `/var/lib/urban-agent` | Keep it on a volume |
| `AGENT_INSECURE` | | `1` allows `http://` (development only) |

## HTTPS: two ways

The control plane sets the host's edge `mode`:

- **`traefik`** (default): the agent runs [Traefik](https://traefik.io) on ports 80 and
  443, which must be free. It routes each website's hostname to it and gets Let's
  Encrypt certificates on its own (`acme_email`). Point the DNS at the host: done.
- **`external`**: the host already has a reverse proxy, with certificates you manage. The
  agent runs no proxy (and stops its Traefik if it ran one, freeing ports 80 and 443).
  Configure the proxy to terminate TLS for each website's hostname and forward to it,
  keeping the `Host` header. Two ways to reach the websites:
  - **The proxy runs in Docker** (edge `network`, e.g. `nginx`): each website's nginx
    joins that network as **`<slug>-nginx`**. Forward to `http://aix-nginx`.
  - **The proxy runs on the host**: each website's nginx is published on
    `127.0.0.1:<http_port>` (never on a public interface). Forward to that port.

  With nginx, for a proxy in Docker:

  ```nginx
  server {
      listen 443 ssl;
      server_name aix.example.org;
      ssl_certificate     /etc/ssl/aix.example.org/fullchain.pem;
      ssl_certificate_key /etc/ssl/aix.example.org/privkey.pem;
      client_max_body_size 100M;

      location / {
          proxy_pass http://aix-nginx;   # or http://127.0.0.1:8101 on the host
          proxy_set_header Host $host;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      }
  }
  ```

  The website's own nginx tells the app the request came over HTTPS.

## Protocol (version 1)

Two calls, both with `Authorization: Bearer <AGENT_TOKEN>`.

### `GET /api/agent/v1/desired-state`

```json
{
  "edge": {"mode": "traefik", "acme_email": "ops@example.org"},
  "agent": {"image_tag": "saas", "version": "saas-1a2b3c4"},
  "tenants": [
    {
      "slug": "aix",
      "generation": 7,
      "state": "running",
      "image_tag": "1.4.0",
      "env": {"TENANT_HOSTNAME": "aix.example.org", "SECRET_KEY": "…", "DB_PASSWORD": "…"}
    },
    {"slug": "arles", "generation": 3, "state": "absent", "purge": true}
  ]
}
```

- `slug`: lowercase letters, digits and dashes, at most 40; the Compose project name.
- `generation`: an integer the control plane increments at every change of the website
  (release, variables, state). The agent deploys when it differs from the one it applied.
- `state`: `running`, `stopped` or `absent` (containers removed; volumes too with `"purge":
  true`).
- `image_tag`: the release (`deploy/README.md`); required unless `absent`.
- `edge`: `mode` (`traefik` or `external`), `acme_email` (required with `traefik`),
  `network` (with `external`: the proxy's Docker network, which must exist).
- `http_port`: with the `external` edge without `network` only, required there: the local
  port (1024–65535, unique on the host) the host's proxy forwards the website's hostname to.
- `env`: the website's variables (`deploy/tenant/.env.example`), uppercase names. Values
  cannot contain `'` or line breaks. `IMAGE`, `IMAGE_TAG` and `TENANT_SLUG` are set by the
  agent and refused here.
- `agent` (optional): `{"image_tag": "saas", "version": "saas-1a2b3c4"}`, the version the
  agent should run (see [Updating itself](#updating-itself)).

## Updating itself

When the desired state names another `agent.version` than its own, the agent, between two
polls:

1. pulls `<AGENT_IMAGE>-agent:<image_tag>` (its own image, never another one) and reads
   the `AGENT_VERSION` built into it. Not the version asked for yet (the image still
   building): it reports so and tries again 10 minutes later;
2. starts a helper from that image (`urban-agent-update`, removed when done), which
   reads the agent's container, removes it, and runs the new image with the same name,
   restart policy, volumes, variables and networks. If the new agent does not start,
   the helper runs the old image again.

The websites keep running throughout. Agents older than this feature are updated by hand
once: `docker pull` the agent image, then recreate the container with the same command.

### `POST /api/agent/v1/report`

Sent after each poll:

```json
{
  "agent_version": "1.4.0",
  "edge": "running",
  "errors": ["invalid slug '../x'"],
  "tenants": [
    {
      "slug": "aix",
      "generation": 7,
      "status": "running",
      "version": "1.4.0",
      "error": "",
      "services": {"web": "healthy", "worker": "running", "migrator": "exited"},
      "stats": {"pages": 12, "users": 40},
      "hint": "",
      "logs": {}
    }
  ],
  "journal": "9f2c4e1ab37d5c08",
  "events": [
    {
      "seq": 41,
      "at": "2026-10-09T08:12:03+00:00",
      "level": "error",
      "slug": "aix",
      "message": "Deployment failed: The database refused the website's password: …",
      "detail": "docker compose -p aix: … service \"migrator\" didn't complete successfully: exit 1\n\n--- migrator\n…"
    }
  ]
}
```

The control plane answers `{"events_ack": 41}`: the last event of this journal it has.

- `edge`: `running` (Traefik), `external`, or what went wrong.
- `generation`: the last one applied successfully (`null` before the first).
- `status`: `running`, `stopped`, `absent`, or `failed` with the reason in `error`. A
  failed deployment is retried after `AGENT_RETRY_SECONDS`, or at once for a new generation.
- `version`: what the website's `/healthz/` reported after the deployment.
- `stats`: the website's figures, counts only (`manage.py tenant_stats` in its `web`
  container): published `pages`, `users` accounts. Collected after each deployment, then
  every `AGENT_STATS_SECONDS` while it runs; `{}` until then, or for a release without
  the command. Other non-negative integers may appear later.
- `hint`: with `failed`, the known cause in plain words, if the agent recognises it (a
  database password refused, a port taken, a release missing from the registry, a full
  disk…); `""` otherwise.
- `logs`: with `failed`, the end of the logs of the services that failed (60 lines, 4,000
  characters, 3 services at most), by service.
- Websites this host runs but the desired state left out are reported too.
- `journal`, `events`: what happened on the host, oldest first, 100 per report: the
  agent starting, deployments (with their duration), failures (with the error and the
  failing services' logs in `detail`), stops, removals, services of a running website
  turning unhealthy and back, edge and update failures, and the control plane being
  unreachable then back. `level` is `info`, `warning` or `error`; `slug` is `""` for the
  host. A failure tried again with the same error is not repeated.
- The events are kept on the host (`journal.json` in the state directory, 500 at most)
  until the control plane acknowledges them with `events_ack`, so those recorded while
  it was unreachable reach it later. `seq` counts up within a `journal`: a new journal id
  (state directory lost) starts again at 1.

## Development

```sh
uv run pytest agent/tests
docker build -f agent/Dockerfile -t urban-agent .
```
