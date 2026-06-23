"""Gunicorn production config.

Auto-loaded when gunicorn is started with ``-c gunicorn.conf.py`` (see the web
service command in docker-compose.yml). Tuned so a single slow or wedged request
can no longer take the whole site down: multiple workers serve in parallel and
``timeout`` force-kills any worker that stops responding instead of letting it
hang forever (the failure mode behind the nginx "upstream timed out" errors).
"""

import multiprocessing
import os

# Bind inside the container; nginx proxies here over the internal network.
bind = "0.0.0.0:8000"

# Workers default to (2 * CPU) + 1, the gunicorn-recommended value, capped so a
# large host does not spawn an unbounded number of memory-hungry workers.
# Override with GUNICORN_WORKERS to tune per deployment.
_default_workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
workers = int(os.environ.get("GUNICORN_WORKERS", _default_workers))

# Threads per worker. With threads > 1 gunicorn uses the gthread worker, which
# handles I/O-bound Django requests (DB, Redis, Brevo) far better than a single
# blocking sync worker.
threads = int(os.environ.get("GUNICORN_THREADS", 2))

# Hard ceiling on request time. A worker stuck past this is killed and replaced,
# so a hung dependency surfaces as a fast 502 instead of an indefinite hang.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", 60))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", 30))

# Keep-alive for nginx upstream connections.
keepalive = 5

# Periodically recycle workers to bound memory growth / leaks. Jitter avoids all
# workers restarting at once.
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", 100))

# Trust X-Forwarded-* from the nginx reverse proxy on the internal network.
forwarded_allow_ips = "*"

# Log to stdout/stderr so docker captures everything.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
