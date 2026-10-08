# Deployment agent

Runs the platform's websites on one host, as the control plane asks. It runs on the
platform's servers and on associations' own machines alike: it only makes outgoing HTTPS
requests, so the host needs no open port besides 80/443 for the websites, and no SSH access.

Every few seconds it fetches the desired state from the control plane, deploys what
changed with Docker Compose ([`deploy/`](../deploy/README.md)), and reports back. It is
standard-library Python driving the Docker CLI: short enough to read before installing.

## What it can and cannot do

The agent drives Docker through its socket, which amounts to root access to the host. It
therefore limits what the control plane can ask of it:

- It only runs images under one name (`AGENT_IMAGE`, `ghcr.io/neikow/urban-platform` by
  default): the control plane chooses a tag, never an image.
- The Compose file comes from that image (`/app/deploy/tenant/compose.yml`), not from the
  control plane.
- Website names, tags and variables are checked before anything reaches Docker; a
  website the control plane leaves out of the desired state is left as it is.
- A website's data is only deleted when the control plane marks it `absent` with
  `purge`. Stopping the agent stops nothing: the websites keep running.

## Installing

Docker Engine with the Compose plugin, and ports 80 and 443 free (the agent starts
[Traefik](https://traefik.io) on them, with Let's Encrypt certificates). Then, with the
token the control plane gives for this host:

```sh
docker run -d --name urban-agent --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v urban-agent:/var/lib/urban-agent \
  -e CONTROL_PLANE_URL=https://control.example.org \
  -e AGENT_TOKEN=<token> \
  ghcr.io/neikow/urban-platform-agent:latest
```

| Variable | Default | |
|---|---|---|
| `CONTROL_PLANE_URL` | | Required, `https://` |
| `AGENT_TOKEN` | | Required: identifies the host |
| `AGENT_IMAGE` | `ghcr.io/neikow/urban-platform` | The only image websites may run (and its `-nginx`) |
| `AGENT_POLL_SECONDS` | `30` | |
| `AGENT_RETRY_SECONDS` | `300` | Delay before trying a failed deployment again |
| `AGENT_STATE_DIR` | `/var/lib/urban-agent` | Keep it on a volume |
| `AGENT_INSECURE` | | `1` allows `http://` (development only) |

## Protocol (version 1)

Two calls, both with `Authorization: Bearer <AGENT_TOKEN>`.

### `GET /api/agent/v1/desired-state`

```json
{
  "edge": {"acme_email": "ops@example.org"},
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
- `env`: the website's variables (`deploy/tenant/.env.example`), uppercase names. Values
  cannot contain `'` or line breaks. `IMAGE`, `IMAGE_TAG` and `TENANT_SLUG` are set by the
  agent and refused here.

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
      "services": {"web": "healthy", "worker": "running", "migrator": "exited"}
    }
  ]
}
```

- `generation`: the last one applied successfully (`null` before the first).
- `status`: `running`, `stopped`, `absent`, or `failed` with the reason in `error`. A
  failed deployment is retried after `AGENT_RETRY_SECONDS`, or at once for a new generation.
- `version`: what the website's `/healthz/` reported after the deployment.
- Websites this host runs but the desired state left out are reported too.

## Development

```sh
uv run pytest agent/tests
docker build -f agent/Dockerfile -t urban-agent .
```
