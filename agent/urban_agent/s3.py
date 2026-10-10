"""Uploads to an S3-compatible bucket (AWS, Scaleway, OVH, Backblaze B2, MinIO…), with
AWS Signature Version 4: the standard library only, like the rest of the agent.

The agent only ever uploads (``PUT``) its backups. Listing them, deleting old ones and
download links are the control plane's job; a restore downloads through links it signs.
"""

import hashlib
import hmac
import http.client
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

TIMEOUT = 300


class S3Error(Exception):
    pass


@dataclass(frozen=True)
class Bucket:
    endpoint: str  # https://s3.fr-par.scw.cloud
    region: str
    bucket: str
    access_key: str
    secret_key: str
    prefix: str = ""

    @classmethod
    def parse(cls, data: Any) -> "Bucket":
        if not isinstance(data, dict):
            raise S3Error("not an object")
        names = ("endpoint", "region", "bucket", "access_key", "secret_key")
        values: dict[str, str] = {}
        for name in names:
            value = data.get(name)
            if not isinstance(value, str) or not value:
                raise S3Error("endpoint, region, bucket, access_key and secret_key are required")
            values[name] = value
        parts = urlsplit(values["endpoint"])
        if parts.scheme != "https" or not parts.netloc or parts.path not in ("", "/"):
            raise S3Error(f"the endpoint must be an https:// address: {values['endpoint']!r}")
        prefix = data.get("prefix") or ""
        if not isinstance(prefix, str) or ".." in prefix or prefix.startswith("/"):
            raise S3Error(f"invalid prefix {prefix!r}")
        if prefix and not prefix.endswith("/"):
            prefix += "/"
        values["endpoint"] = values["endpoint"].rstrip("/")
        return cls(**values, prefix=prefix)

    @property
    def host(self) -> str:
        return urlsplit(self.endpoint).netloc

    def path(self, key: str) -> str:
        """Path-style: /<bucket>/<key>, which every provider accepts."""
        return "/" + quote(f"{self.bucket}/{key}", safe="/-_.~")


def _hmac(key: bytes, text: str) -> bytes:
    return hmac.new(key, text.encode(), hashlib.sha256).digest()


def sign(
    method: str,
    path: str,
    headers: dict[str, str],
    payload_hash: str,
    *,
    access_key: str,
    secret_key: str,
    region: str,
    now: datetime,
    query: str = "",
) -> str:
    """The Authorization header of a request (AWS Signature Version 4). ``headers``,
    lowercase, are all signed; they include host, x-amz-date and x-amz-content-sha256."""
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    day = amz_date[:8]
    names = sorted(headers)
    canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in names)
    signed_headers = ";".join(names)
    canonical_request = "\n".join(
        [method, path, query, canonical_headers, signed_headers, payload_hash]
    )
    scope = f"{day}/{region}/s3/aws4_request"
    string_to_sign = "\n".join(
        [
            "AWS4-HMAC-SHA256",
            amz_date,
            scope,
            hashlib.sha256(canonical_request.encode()).hexdigest(),
        ]
    )
    key = _hmac(
        _hmac(_hmac(_hmac(f"AWS4{secret_key}".encode(), day), region), "s3"), "aws4_request"
    )
    signature = hmac.new(key, string_to_sign.encode(), hashlib.sha256).hexdigest()
    return (
        f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )


def put(bucket: Bucket, key: str, file: Path, sha256: str, now: datetime | None = None) -> None:
    """Upload ``file`` as ``key``; ``sha256`` is its hash, signed: providers that check it
    (AWS among them) refuse an upload corrupted on the way."""
    now = now or datetime.now(UTC)
    path = bucket.path(key)
    size = file.stat().st_size
    headers = {
        "host": bucket.host,
        "content-length": str(size),
        "x-amz-content-sha256": sha256,
        "x-amz-date": now.strftime("%Y%m%dT%H%M%SZ"),
    }
    authorization = sign(
        "PUT",
        path,
        headers,
        sha256,
        access_key=bucket.access_key,
        secret_key=bucket.secret_key,
        region=bucket.region,
        now=now,
    )
    connection = http.client.HTTPSConnection(bucket.host, timeout=TIMEOUT)
    try:
        with file.open("rb") as body:
            connection.request(
                "PUT", path, body=body, headers={**headers, "Authorization": authorization}
            )
            response = connection.getresponse()
            detail = response.read(2000).decode(errors="replace")
    except OSError as error:
        raise S3Error(f"upload of {key}: {error}") from error
    finally:
        connection.close()
    if response.status >= 300:
        raise S3Error(f"upload of {key}: HTTP {response.status} {detail.strip()[:500]}")
