"""Una API falsa de typesearch, por HTTP de verdad, que cumple el contrato del OpenAPI.

Valida cada pedido contra el esquema de su ruta (como la API, rechaza campos desconocidos con
400 invalid_request) y cada respuesta que manda contra el esquema de la respuesta: las pruebas fallan si
el SDK manda algo que la API no acepta o si un ejemplo se aleja del contrato.

``api.next(...)`` encola respuestas armadas a mano (errores, 429, cortes, flujos rotos) que se usan
antes que las normales, en orden.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from jsonschema import Draft202012Validator, FormatChecker

OPENAPI = json.loads((Path(__file__).resolve().parent.parent / "openapi" / "openapi.json").read_text(encoding="utf-8"))
_VALIDATORS: Dict[str, Draft202012Validator] = {}

KEY = "ts_test_0123456789"


def validator(name: str) -> Draft202012Validator:
    if name not in _VALIDATORS:
        schema = {"components": OPENAPI["components"], "$ref": f"#/components/schemas/{name}"}
        _VALIDATORS[name] = Draft202012Validator(schema, format_checker=FormatChecker())
    return _VALIDATORS[name]


def check(name: str, body: Any) -> None:
    """Falla si un ejemplo no cumple el esquema del contrato."""
    errors = list(validator(name).iter_errors(body))
    if errors:
        raise AssertionError(f"El ejemplo no cumple {name}: {errors[0].message} en {list(errors[0].absolute_path)}")


# --- Ejemplos que cumplen el contrato ---------------------------------------------------------


def result(n: int, **extra: Any) -> Dict[str, Any]:
    return {
        "url": f"https://diarioejemplo.example/economia/nota-{n}",
        "title": f"El dólar cerró estable por {n}ª rueda",
        "source": "Diario Ejemplo",
        "country": "AR",
        "language": "es",
        "published_at": "2026-09-21T18:05:00.000Z",
        "section": "economia",
        "snippet": "La divisa se mantuvo sin cambios frente al cierre anterior.",
        "score": 0.96 - n / 100,
        "headline_relevance": 0.91,
        "read": None,
        "highlights": [],
        "tone": None,
        "answers": None,
        "duplicates": [],
        "date_match": None,
        "referenced_date": None,
        "found_in": "index",
        **extra,
    }


def search_response(**extra: Any) -> Dict[str, Any]:
    return {
        "id": "req_fake0001",
        "object": "search",
        "mode": "fast",
        "queries": ["el dólar"],
        "found": True,
        "total": 2,
        "results": [result(1), result(2, url="https://reddiaria.example/economia/nota-2", source="Red Diaria")],
        "groups": None,
        "near_misses": [],
        "rejected": [],
        "diffusion": None,
        "tone": None,
        "essential": None,
        "reference": None,
        "temporal": None,
        "site": None,
        "index": None,
        "usage": {
            "tokens": 1840,
            "calls": 2,
            "cost_usd": 0,
            "headlines": 160,
            "from_memory": 12,
            "pages_direct": 0,
            "pages_browser": 0,
            "duration_ms": 910,
        },
        "budget": None,
        "discovery": None,
        "incomplete": False,
        "cached_at": None,
        "warnings": [],
        **extra,
    }


def problem(status: int, code: str, **extra: Any) -> Dict[str, Any]:
    return {
        "type": f"urn:typesearch:error:{code}",
        "title": code,
        "status": status,
        "detail": f"detail of {code}",
        "code": code,
        "request_id": "req_fakeerr1",
        **extra,
    }


def job(job_id: str, status: str, **extra: Any) -> Dict[str, Any]:
    return {
        "id": job_id,
        "object": "job",
        "status": status,
        "created_at": "2026-09-22T14:03:11.000Z",
        "finished_at": None,
        "result": None,
        "error": None,
        **extra,
    }


def usage() -> Dict[str, Any]:
    return {
        "object": "usage",
        "key": {"id": "ts_live_Xk3P9qaB", "name": "Production"},
        "limits": {"tokens_per_day": 1000000, "requests_per_minute": 600, "requests_per_second": 10},
        "today": {"requests": 412, "tokens": 183920, "cost_usd": 0.41, "remaining_tokens": 816080},
        "last_30_days": {"requests": 9120, "tokens": 4102330, "cost_usd": 9.12},
        "credit": {"balance_usd": 42.6, "plan": "payg", "spent_this_month_usd": 9.12, "monthly_limit_usd": None},
        # Precios de mentira: los reales están en typesearch.ai/pricing.
        "pricing": {
            "currency": "USD",
            "per_1000_requests": {"ultra": 0, "fast": 0, "normal": 0, "deep": 0, "similar": 0, "similar_deep": 0, "site_search": 0},
            "per_1000_pages": {"contents": 0, "contents_with_query": 0},
        },
    }


STEP = {"id": "juicio-indice", "text": "The model reads 160 headlines from the index", "status": "running", "detail": None}


@dataclass
class Scripted:
    status: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    body: Any = None
    events: Optional[List[Dict[str, Any]]] = None
    raw: Optional[str] = None
    destroy: bool = False
    delay: float = 0
    hang: bool = False


@dataclass
class Recorded:
    method: str
    path: str
    query: Dict[str, List[str]]
    headers: Dict[str, str]
    body: Any


class FakeApi:
    def __init__(self) -> None:
        self.requests: List[Recorded] = []
        self.closed_early = 0
        self._queue: List[Scripted] = []
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        api = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: Any) -> None:
                pass

            def do_GET(self) -> None:
                api._handle(self)

            def do_POST(self) -> None:
                api._handle(self)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def next(self, *responses: Scripted) -> FakeApi:
        with self._lock:
            self._queue.extend(responses)
        return self

    def reset(self) -> None:
        with self._lock:
            self.requests.clear()
            self._queue.clear()
            self._jobs.clear()
            self.closed_early = 0

    @property
    def last(self) -> Recorded:
        return self.requests[-1]

    def wait_closed(self, n: int = 1, timeout: float = 3) -> bool:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if self.closed_early >= n:
                return True
            time.sleep(0.01)
        return False

    # --- Rutas ---------------------------------------------------------------------------

    def _handle(self, h: BaseHTTPRequestHandler) -> None:
        url = urlparse(h.path)
        length = int(h.headers.get("content-length") or 0)
        text = h.rfile.read(length).decode("utf-8") if length else ""
        try:
            body: Any = json.loads(text) if text else None
        except ValueError:
            body = text
        with self._lock:
            self.requests.append(Recorded(h.command, url.path, parse_qs(url.query), {k.lower(): v for k, v in h.headers.items()}, body))
            scripted = self._queue.pop(0) if self._queue else None
        if scripted is not None:
            return self._scripted(h, scripted)

        auth = h.headers.get("authorization") or (f"Bearer {h.headers['x-api-key']}" if h.headers.get("x-api-key") else None)
        if not auth:
            return self._json(h, 401, problem(401, "missing_api_key"), "Problem")
        if auth != f"Bearer {KEY}":
            return self._json(h, 401, problem(401, "invalid_api_key"), "Problem")

        ruta = f"{h.command} {url.path}"
        if ruta == "POST /v1/search":
            return self._search(h, body, "SearchRequest", "search")
        if ruta == "POST /v1/similar":
            return self._search(h, body, "SimilarRequest", "similar")
        if ruta == "POST /v1/search/site":
            return self._site(h, body)
        if ruta == "POST /v1/contents":
            return self._contents(h, body)
        if h.command == "GET" and url.path.startswith("/v1/jobs/"):
            return self._job(h, unquote(url.path[len("/v1/jobs/") :]))
        if ruta == "GET /v1/usage":
            return self._json(h, 200, usage(), "Usage")
        return self._json(h, 404, problem(404, "not_found"), "Problem")

    def _invalid(self, h: BaseHTTPRequestHandler, body: Any, esquema: str) -> bool:
        errors = sorted(validator(esquema).iter_errors(body), key=lambda e: list(e.absolute_path))
        if not errors:
            return False
        detalle = [{"path": ".".join(str(p) for p in e.absolute_path) or "(body)", "message": e.message} for e in errors]
        self._json(
            h, 400, problem(400, "invalid_request", detail=f"{detalle[0]['path']}: {detalle[0]['message']}", errors=detalle), "Problem"
        )
        return True

    def _search(self, h: BaseHTTPRequestHandler, body: Any, esquema: str, obj: str) -> None:
        if self._invalid(h, body, esquema):
            return
        queries = [] if obj == "similar" else (body["query"] if isinstance(body["query"], list) else [body["query"]])
        reference = {"url": body["url"], "title": "Inflación: qué esperan los analistas"} if obj == "similar" else None
        r = search_response(object=obj, mode=body.get("mode", "normal"), queries=queries, reference=reference)
        if body.get("stream"):
            return self._stream(h, r)
        self._json(h, 200, r, "SearchResponse")

    def _site(self, h: BaseHTTPRequestHandler, body: Any) -> None:
        if self._invalid(h, body, "SiteSearchRequest"):
            return
        r = search_response(object="site_search", mode=body.get("mode", "normal"), queries=[body["query"]], site=body["site"], index=None)
        if body.get("stream"):
            return self._stream(h, r)
        with self._lock:
            job_id = f"job_fake{len(self._jobs) + 1}"
            self._jobs[job_id] = {"polls": 0, "fail": "fail" in body["site"], "site": body["site"]}
        self._json(h, 202, job(job_id, "queued"), "Job", {"Location": f"/v1/jobs/{job_id}"})

    def _job(self, h: BaseHTTPRequestHandler, job_id: str) -> None:
        with self._lock:
            j = self._jobs.get(job_id)
            if j is not None:
                j["polls"] += 1
        if j is None:
            return self._json(h, 404, problem(404, "job_not_found"), "Problem")
        if j["polls"] < 2:
            return self._json(h, 200, job(job_id, "running"), "Job")
        if j["fail"]:
            error = problem(502, "site_unreachable", detail="The site did not answer.")
            return self._json(h, 200, job(job_id, "failed", finished_at="2026-09-22T14:03:39.000Z", error=error), "Job")
        r = search_response(id=job_id, object="site_search", mode="normal", site=j["site"], index=None)
        self._json(h, 200, job(job_id, "succeeded", finished_at="2026-09-22T14:03:39.000Z", result=r), "Job")

    def _contents(self, h: BaseHTTPRequestHandler, body: Any) -> None:
        if self._invalid(h, body, "ContentsRequest"):
            return
        vacio = {
            "title": None,
            "description": None,
            "published_at": None,
            "source": None,
            "excerpt": None,
            "highlights": [],
            "relevance": None,
        }
        results = []
        for u in body["urls"]:
            if "unreachable" in u:
                results.append(
                    {"url": u, "status": "error", "error": {"code": "site_unreachable", "message": "The site did not answer."}, **vacio}
                )
            else:
                results.append(
                    {
                        "url": u,
                        "status": "ok",
                        "error": None,
                        "title": "Presupuesto 2027: las claves del proyecto",
                        "description": "El Gobierno envió el proyecto al Congreso.",
                        "published_at": "2026-09-16T01:12:00.000Z",
                        "source": "Red Diaria",
                        "excerpt": "El proyecto prevé un superávit primario…",
                        "highlights": ["El proyecto prevé un superávit primario…"] if body.get("query") else [],
                        "relevance": 0.97 if body.get("query") else None,
                    }
                )
        out = {
            "id": "req_fakecont",
            "object": "contents",
            "results": results,
            "usage": {"tokens": 1320, "calls": 1, "cost_usd": 0, "duration_ms": 1840},
        }
        self._json(h, 200, out, "ContentsResponse")

    # --- Salida --------------------------------------------------------------------------

    def _stream(self, h: BaseHTTPRequestHandler, final: Dict[str, Any]) -> None:
        partial = {**final, "results": final["results"][:1], "usage": {**final["usage"], "cost_usd": None}}
        self._sse(
            h,
            [
                {"event": "step", "data": STEP},
                {"event": "partial", "data": partial},
                {"event": "step", "data": {**STEP, "status": "done"}},
                {"event": "result", "data": final},
            ],
        )

    def _sse(self, h: BaseHTTPRequestHandler, events: List[Dict[str, Any]], hang: bool = False) -> None:
        for e in events:
            if e["event"] in ("partial", "result"):
                check("SearchResponse", e["data"])
            if e["event"] == "error":
                check("Problem", e["data"])
        h.send_response(200)
        h.send_header("Content-Type", "text/event-stream; charset=utf-8")
        h.send_header("X-Request-Id", "req_fakesse1")
        h.end_headers()
        chunks = [": latido\n\n"] + [f"event: {e['event']}\ndata: {json.dumps(e['data'])}\n\n" for e in events]
        self._write(h, "".join(chunks), hang)

    def _write(self, h: BaseHTTPRequestHandler, text: str, hang: bool) -> None:
        try:
            h.wfile.write(text.encode("utf-8"))
            h.wfile.flush()
            if hang:
                # Queda abierto hasta que el cliente corte: lo notamos al escribir el latido.
                end = time.monotonic() + 10
                while time.monotonic() < end:
                    time.sleep(0.05)
                    h.wfile.write(b": latido\n\n")
                    h.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            with self._lock:
                self.closed_early += 1

    def _json(self, h: BaseHTTPRequestHandler, status: int, body: Any, esquema: str, headers: Optional[Dict[str, str]] = None) -> None:
        check(esquema, body)
        data = json.dumps(body).encode("utf-8")
        h.send_response(status)
        h.send_header("Content-Type", "application/problem+json; charset=utf-8" if status >= 400 else "application/json; charset=utf-8")
        h.send_header("X-Request-Id", "req_fake0001")
        h.send_header("X-RateLimit-Limit", "600")
        h.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            h.send_header(k, v)
        h.end_headers()
        h.wfile.write(data)

    def _scripted(self, h: BaseHTTPRequestHandler, s: Scripted) -> None:
        if s.delay:
            time.sleep(s.delay)
        if s.destroy:
            h.close_connection = True
            return
        if s.raw is not None:
            h.send_response(s.status)
            h.send_header("Content-Type", "text/event-stream")
            h.end_headers()
            return self._write(h, s.raw, s.hang)
        if s.events is not None:
            return self._sse(h, s.events, s.hang)
        data = b"" if s.body is None else (s.body if isinstance(s.body, str) else json.dumps(s.body)).encode("utf-8")
        try:
            h.send_response(s.status)
            h.send_header("Content-Type", "application/problem+json" if s.status >= 400 else "application/json")
            h.send_header("X-Request-Id", "req_fakescr1")
            h.send_header("Content-Length", str(len(data)))
            for k, v in s.headers.items():
                h.send_header(k, v)
            h.end_headers()
            h.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass
