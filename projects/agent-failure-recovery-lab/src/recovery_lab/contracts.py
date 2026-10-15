import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Request(Strict):
    task_id: str = Field(pattern=r"^[a-z0-9-]{1,64}$")
    quantity: int = Field(ge=1, le=10)


class Receipt(Request):
    effect_count: int = Field(ge=1, le=1)


class Fault(Strict):
    mode: str = Field(pattern=r"^(none|http500|rate429|malformed|delay|hold|dependency)$")
    failures: int = Field(default=2, ge=0, le=3)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def local_url(url: str) -> str:
    p = urlparse(url)
    if (
        p.scheme != "http"
        or p.hostname
        not in {"127.0.0.1", "localhost", "backend", "toxiproxy", "prometheus", "grafana"}
        or p.username
        or p.password
        or p.path not in ("", "/")
        or p.query
        or p.fragment
    ):
        raise ValueError("only lab loopback or fixed Compose service HTTP origins are allowed")
    return url.rstrip("/")


def call(base: str, path: str, body=None, timeout=2.0, method=None):
    base = local_url(base)
    payload = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(
        base + path, data=payload, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.build_opener(NoRedirect, urllib.request.ProxyHandler({})).open(
        request, timeout=timeout
    ) as response:
        data = response.read(65537)
        if len(data) > 65536:
            raise ValueError("response exceeds budget")
        return json.loads(data) if data else None
