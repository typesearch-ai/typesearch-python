#!/usr/bin/env python3
"""Genera src/typesearch/_models.py y _params.py a partir del OpenAPI de la API.

    python scripts/generate_models.py             desde la copia de openapi/openapi.json
    python scripts/generate_models.py --fetch     baja el OpenAPI vivo, actualiza la copia y regenera
    python scripts/generate_models.py --from X    desde otro OpenAPI (archivo o URL: una rama de la API)
    python scripts/generate_models.py --check     falla si los archivos generados no están al día

Las respuestas salen como modelos de pydantic (`_models.py`) y las opciones de cada método como
TypedDict (`_params.py`). El OpenAPI define cada respuesta entera, sin $ref: cada objeto se identifica
por su forma (sin descripciones ni límites) y se declara una sola vez, con el nombre de NOMBRES según dónde
aparece primero. Un objeto nuevo que no esté en NOMBRES recibe un nombre armado con la ruta y un aviso.

La misma tabla de nombres que scripts/generate-types.mjs de typesearch-js: los tipos se llaman igual en
los dos SDKs. Sólo usa la biblioteca estándar.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import keyword
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

RAIZ = Path(__file__).resolve().parent.parent
COPIA = RAIZ / "openapi" / "openapi.json"
MODELOS = RAIZ / "src" / "typesearch" / "_models.py"
PARAMETROS = RAIZ / "src" / "typesearch" / "_params.py"
VIVO = "https://api.typesearch.ai/v1/openapi.json"

RESPUESTAS = ["SearchResponse", "ContentsResponse", "Problem", "Job", "Sources", "Source", "Usage"]

# Las opciones de cada método: el cuerpo del pedido sin los argumentos posicionales.
OPCIONES = {
    "SearchRequest": (
        "SearchOptions",
        ["query", "stream"],
        "Keyword arguments of ``search()`` and ``search_stream()``: every field of ``POST /v1/search`` but ``query``.",
    ),
    "SimilarRequest": ("SimilarOptions", ["url"], "Keyword arguments of ``similar()``: every field of ``POST /v1/similar`` but ``url``."),
    "SiteSearchRequest": (
        "SiteSearchOptions",
        ["site", "query", "stream"],
        "Keyword arguments of ``site_search()``: every field of ``POST /v1/search/site`` but ``site`` and ``query``.",
    ),
    "ContentsRequest": (
        "ContentsOptions",
        ["urls"],
        "Keyword arguments of ``contents()``: every field of ``POST /v1/contents`` but ``urls``.",
    ),
}

NOMBRES = {
    "SearchRequest.mode": "Mode",
    "SearchRequest.questions{}": "Question",
    "SearchRequest.questions{}<boolean>": "BooleanQuestion",
    "SearchRequest.questions{}<boolean>.criteria": "BooleanCriteria",
    "SearchRequest.questions{}<choice>": "ChoiceQuestion",
    "SearchRequest.questions{}<score>": "ScoreQuestion",
    "SearchResponse.mode": "Mode",
    "SearchResponse.results[]": "Result",
    "SearchResponse.results[].read": "Reading",
    "SearchResponse.results[].tone": "ResultTone",
    "SearchResponse.results[].answers": "Answers",
    "SearchResponse.results[].answers.values{}": "Answer",
    "SearchResponse.results[].answers.values{}<boolean>": "BooleanAnswer",
    "SearchResponse.results[].answers.values{}<choice>": "ChoiceAnswer",
    "SearchResponse.results[].answers.values{}<score>": "ScoreAnswer",
    "SearchResponse.results[].duplicates[]": "Duplicate",
    "SearchResponse.groups[]": "QueryGroup",
    "SearchResponse.groups[].diffusion": "Diffusion",
    "SearchResponse.groups[].diffusion.by_day[]": "DiffusionDay",
    "SearchResponse.groups[].diffusion.by_source[]": "DiffusionSource",
    "SearchResponse.groups[].diffusion.first": "FirstPublication",
    "SearchResponse.groups[].tone": "ToneSummary",
    "SearchResponse.groups[].tone.overall": "ToneCounts",
    "SearchResponse.groups[].tone.by_source[]": "SourceTone",
    "SearchResponse.groups[].essential": "Essential",
    "SearchResponse.groups[].essential.excerpts[]": "EssentialExcerpt",
    "SearchResponse.groups[].temporal": "QueryDate",
    "SearchResponse.groups[].temporal.window": "DateWindow",
    "SearchResponse.reference": "Reference",
    "SearchResponse.index": "IndexInfo",
    "SearchResponse.usage": "SearchUsage",
    "SearchResponse.budget": "Budget",
    "SearchResponse.discovery": "Discovery",
    "SearchResponse.warnings[]": "ResponseWarning",
    "ContentsResponse.results[]": "ContentsResult",
    "ContentsResponse.results[].error": "ContentsError",
    "ContentsResponse.usage": "ContentsUsage",
    "Problem.errors[]": "FieldError",
    "Sources.by_country[]": "CountryCoverage",
    "Sources.by_language[]": "LanguageCoverage",
    "Usage.key": "UsageKey",
    "Usage.limits": "UsageLimits",
    "Usage.today": "UsageToday",
    "Usage.last_30_days": "UsagePeriod",
    "Usage.credit": "Credit",
    "Usage.pricing": "Pricing",
    "Usage.pricing.per_1000_requests": "RequestPricing",
    "Usage.pricing.per_1000_pages": "PagePricing",
}

# Descripciones para los campos que el OpenAPI todavía no describe (se usan sólo si falta la suya).
DOCS = {
    "Result.url": "The article URL.",
    "Result.title": "The headline.",
    "Result.source": "The outlet that published it.",
    "Result.published_at": "Publication date-time (ISO 8601, UTC), when known.",
    "Result.section": "The section the outlet declares, or the first segment of the URL path.",
    "Result.headline_relevance": "Probability that the headline alone is about the query.",
    "Result.read": "Set when the article was opened and read: its probability and how central the topic is (0–3).",
    "Result.highlights": "Short verbatim excerpts about the query (up to 25 words), from articles that were read.",
    "Result.tone": "Tone relative to the query, when ``tone=True``.",
    "Result.answers": "Answers to your ``questions``, when you asked some.",
    "Result.duplicates": "The same story from other outlets, when ``dedupe=True``.",
    "SearchResponse.id": "The request id, also in the ``X-Request-Id`` header.",
    "SearchResponse.found": "Whether any result scored 0.5 or more.",
    "SearchResponse.total": "How many relevant articles exist; it can be more than ``max_results``.",
    "SearchResponse.results": "The relevant articles, most relevant first.",
    "SearchResponse.diffusion": "Articles per day and per source, and who published first.",
    "SearchResponse.tone": "Tone counts overall and by source, when ``tone=True``.",
    "SearchResponse.essential": "Up to three verbatim excerpts that capture the story, when ``essential`` is on.",
    "SearchResponse.reference": "The reference article, in a ``similar`` response.",
    "SearchResponse.site": "The site searched, in a live site search.",
    "SearchResponse.usage": "Model tokens, calls, time and what this request was billed (``cost_usd``).",
    "SearchResponse.budget": "The ``max_tokens`` cap and how much of it was used.",
    "SearchResponse.cached_at": "When the cached result was computed; ``None`` if it was computed now.",
    "SearchResponse.warnings": "Things that did not stop the request, such as a domain that is not indexed.",
    "ContentsResult.status": "``ok``, or ``error`` with the reason in ``error``. One URL failing never fails the request.",
    "ContentsResult.excerpt": "A short verbatim excerpt (up to 25 words, never from the first paragraph).",
    "ContentsResult.relevance": "With a ``query``: probability that the page is about it.",
    "Job.status": "``queued``, ``running``, ``succeeded`` (with ``result``) or ``failed`` (with ``error``).",
    "Job.result": "The search response, once the job succeeded.",
    "Job.error": "The problem details, if the job failed.",
    "Source.covered": "Whether the domain is in the index.",
    "Usage.today": "Since 00:00 UTC.",
    "Usage.credit": "The prepaid credit of the organization.",
    "Usage.pricing": "The price list, in USD per 1,000 requests or pages.",
}

SIN_FORMA = {
    "description",
    "title",
    "examples",
    "default",
    "pattern",
    "format",
    "minLength",
    "maxLength",
    "minimum",
    "maximum",
    "minItems",
    "maxItems",
    "propertyNames",
    "additionalProperties",
}


def es_json(nombre: str) -> bool:
    """Un valor JSON cualquiera: los ``*___schemaN`` recursivos que genera zod."""
    return re.search(r"___schema\d+$", nombre) is not None


class Generador:
    def __init__(self, spec: Dict[str, Any]) -> None:
        self.spec = spec
        self.esquemas: Dict[str, Any] = spec["components"]["schemas"]
        self.declaraciones: Dict[str, Optional[str]] = {}
        self.por_forma: Dict[str, str] = {}
        self.avisos: List[str] = []
        self.lado = "respuesta"  # "pedido": TypedDict · "respuesta": modelo de pydantic

    # --- Forma ---------------------------------------------------------------------------

    def forma(self, e: Any) -> Any:
        if isinstance(e, list):
            return [self.forma(x) for x in e]
        if not isinstance(e, dict):
            return e
        if "$ref" in e:
            n = e["$ref"].split("/")[-1]
            return {"json": True} if es_json(n) else self.forma(self.esquemas[n])
        f: Dict[str, Any] = {}
        for k in sorted(e):
            v = e[k]
            if k == "properties":
                f[k] = {p: self.forma(s) for p, s in v.items()}
            elif k == "additionalProperties":
                f[k] = self.forma(v) if isinstance(v, dict) else v
            elif k == "propertyNames":
                if "enum" in v:
                    f[k] = {"enum": v["enum"]}
            elif k not in SIN_FORMA:
                f[k] = self.forma(v)
        return f

    def clave(self, e: Any) -> str:
        return f"{self.lado}:{json.dumps(self.forma(e), sort_keys=True, ensure_ascii=False)}"

    # --- Nombres -------------------------------------------------------------------------

    def nombrar(self, ruta: str) -> str:
        if ruta in NOMBRES:
            return NOMBRES[ruta]
        partes = ruta.split(".")
        ultimo = re.sub(r"\[\]|\{\}|<.*>", "", partes[-1]) if len(partes) > 1 else ""
        nombre = pascal(partes[0]) + pascal(ultimo)
        self.avisos.append(f"Sin nombre en NOMBRES: {ruta} → {nombre}")
        return nombre

    def reservar(self, nombre: str) -> str:
        n, i = nombre, 2
        while n in self.declaraciones:
            n, i = f"{nombre}{i}", i + 1
        if n != nombre:
            self.avisos.append(f"Nombre repetido: {nombre} → {n}")
        self.declaraciones[n] = None
        return n

    # --- Tipos ---------------------------------------------------------------------------

    def tipo(self, e: Dict[str, Any], ruta: str) -> str:
        if "$ref" in e:
            n = e["$ref"].split("/")[-1]
            return "JsonValue" if es_json(n) else self.objeto(self.esquemas[n], n)
        variantes = e.get("anyOf") or e.get("oneOf")
        if variantes:
            return self.union(variantes, ruta)
        if "const" in e:
            return f"Literal[{json.dumps(e['const'])}]"
        if "enum" in e:
            return self.enumeracion(e, ruta)
        t = e.get("type")
        if isinstance(t, list):
            return juntar([self.tipo({**e, "type": x}, ruta) for x in t])
        if t == "string":
            if self.lado == "pedido" and e.get("format") in ("date", "date-time"):
                return "DateLike"
            return "str"
        if t == "integer":
            return "int"
        if t == "number":
            return "float"
        if t == "boolean":
            return "bool"
        if t == "null":
            return "None"
        if t == "array":
            item = self.tipo(e.get("items", {}), f"{ruta}[]")
            return f"Sequence[{item}]" if self.lado == "pedido" else f"List[{item}]"
        if t == "object":
            if "properties" in e:
                return self.objeto(e, ruta)
            ap = e.get("additionalProperties")
            valor = self.tipo(ap, f"{ruta}{{}}") if isinstance(ap, dict) else "Any"
            return f"Mapping[str, {valor}]" if self.lado == "pedido" else f"Dict[str, {valor}]"
        return "Any"

    def enumeracion(self, e: Dict[str, Any], ruta: str) -> str:
        t = f"Literal[{', '.join(json.dumps(v) for v in e['enum'])}]"
        k = f"enum:{t}"
        if k in self.por_forma:
            return self.por_forma[k]
        if ruta not in NOMBRES:
            return t
        n = self.reservar(NOMBRES[ruta])
        self.por_forma[k] = n
        self.declaraciones[n] = f"{n} = {t}\n{docstring_suelto(e.get('description'))}"
        return n

    def union(self, variantes: List[Dict[str, Any]], ruta: str) -> str:
        objetos = [v for v in variantes if v.get("type") == "object" and "properties" in v]
        if len(objetos) > 1 and all("const" in o["properties"].get("type", {}) for o in objetos):
            k = f"union:{self.clave({'anyOf': variantes})}"
            if k in self.por_forma:
                return self.por_forma[k]
            n = self.reservar(self.nombrar(ruta))
            self.por_forma[k] = n
            miembros = [self.tipo(v, f"{ruta}<{v['properties']['type']['const']}>") for v in variantes]
            self.declaraciones[n] = f"{n} = Union[{', '.join(miembros)}]\n"
            return n
        return juntar([self.tipo(v, ruta) for v in variantes])

    def objeto(self, e: Dict[str, Any], ruta: str) -> str:
        k = self.clave(e)
        if k in self.por_forma:
            existente = self.por_forma[k]
            propio = NOMBRES.get(ruta)
            if not propio or propio == existente or propio in self.declaraciones:
                return propio if propio and propio in self.declaraciones else existente
            self.declaraciones[propio] = f"{propio} = {existente}\n"
            return propio
        n = self.reservar(ruta if ruta in self.esquemas else self.nombrar(ruta))
        self.por_forma[k] = n
        self.declaraciones[n] = self.clase(n, e, ruta)
        return n

    def clase(self, n: str, e: Dict[str, Any], ruta: str, sin: Optional[List[str]] = None, docu: Optional[str] = None) -> str:
        requeridos = set(e.get("required", []))
        lineas: List[str] = []
        doc_clase = docu or e.get("description")
        for p, s in e["properties"].items():
            if sin and p in sin:
                continue
            t = self.tipo(s, f"{ruta}.{p}")
            texto = " ".join(x for x in [s.get("description") or DOCS.get(f"{n}.{p}"), limites(s) if self.lado == "pedido" else ""] if x)
            nombre = p
            if keyword.iskeyword(p) or p in ("json", "copy", "schema", "construct", "validate", "dict", "fields"):
                nombre = f"{p}_"
            if self.lado == "pedido":
                if not identificador(p):
                    raise ValueError(f"{ruta}.{p}: un TypedDict con clase no admite este nombre")
                envoltura = "Required" if p in requeridos else "NotRequired"
                lineas.append(f"    {p}: {envoltura}[{t}]")
            else:
                opcional = p not in requeridos
                anotacion = f"Optional[{t}]" if opcional and not t.startswith("Optional[") and t != "None" else t
                if nombre != p:
                    lineas.append(f'    {nombre}: {anotacion} = Field({"None, " if opcional else ""}alias="{p}")')
                else:
                    lineas.append(f"    {nombre}: {anotacion}{' = None' if opcional else ''}")
            if texto:
                lineas.append(f"    {docstring(texto, 4)}")
        base = "TypedDict, total=False" if self.lado == "pedido" else "_Model"
        cuerpo = "\n".join(lineas) or "    pass"
        cabecera = f"class {n}({base}):\n"
        if doc_clase:
            cabecera += f"    {docstring(doc_clase, 4)}\n\n"
        return cabecera + cuerpo + "\n"

    # --- Salida --------------------------------------------------------------------------

    def modelos(self) -> str:
        self.lado = "respuesta"
        self.declaraciones, self.por_forma = {}, {}
        for c in RESPUESTAS:
            if c not in self.esquemas:
                raise SystemExit(f"El OpenAPI no tiene components.schemas.{c}")
            self.objeto(self.esquemas[c], c)
        clases = [n for n, d in self.declaraciones.items() if d and d.startswith("class ")]
        cuerpo = self.cuerpo()
        return f'''{self.cabecera()}
"""Response models of the typesearch API, generated from its OpenAPI document."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

__all__ = {json.dumps(sorted(n for n in self.declaraciones), indent=4).replace(chr(10) + "]", "," + chr(10) + "]")}


class _Model(BaseModel):
    """Every response model keeps the fields it does not know, so a newer API never breaks an older SDK."""

    model_config = ConfigDict(extra="allow", populate_by_name=True, use_attribute_docstrings=True, protected_namespaces=())

    # Built without validation, a model can hold values its annotations do not expect (a new enum value): no
    # serializer warnings for them.
    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        kwargs.setdefault("warnings", False)
        return super().model_dump(*args, **kwargs)

    def model_dump_json(self, *args: Any, **kwargs: Any) -> str:
        kwargs.setdefault("warnings", False)
        return super().model_dump_json(*args, **kwargs)


{cuerpo}

for _model in ({", ".join(clases)},):
    _model.model_rebuild()
'''

    def parametros(self) -> str:
        self.lado = "pedido"
        self.declaraciones, self.por_forma = {}, {}
        for c, (nombre, sin, docu) in OPCIONES.items():
            if c not in self.esquemas:
                raise SystemExit(f"El OpenAPI no tiene components.schemas.{c}")
            n = self.reservar(nombre)
            self.declaraciones[n] = self.clase(n, self.esquemas[c], c, sin=sin, docu=docu)
        cuerpo = self.cuerpo()
        nulos = sorted({p for c in OPCIONES for p, e in self.esquemas[c]["properties"].items() if acepta_null(e)})
        return f'''{self.cabecera()}
"""Request options of the typesearch API, generated from its OpenAPI document."""

from __future__ import annotations

import datetime as _dt
from typing import Any, FrozenSet, List, Mapping, Optional, Sequence, Union

from typing_extensions import Literal, NotRequired, Required, TypedDict

__all__ = {json.dumps(sorted(["DateLike", "JsonValue", "NULLABLE", *self.declaraciones]), indent=4).replace(chr(10) + "]", "," + chr(10) + "]")}

DateLike = Union[str, _dt.date, _dt.datetime]
"""A date (``"2026-09-20"`` or ``datetime.date``) or a date-time with a time zone (a string or an aware ``datetime``)."""

JsonValue = Union[str, int, float, bool, None, List[Any], Mapping[str, Any]]
"""Any JSON value."""

NULLABLE: FrozenSet[str] = frozenset({json.dumps(nulos)[1:-1].join("{}")})
"""Options where ``None`` means something (``days=None``: the whole index) and is sent as ``null``."""


{cuerpo}'''

    def cuerpo(self) -> str:
        """Las enumeraciones primero, después las clases y al final las uniones y los alias, que se evalúan
        al importar el módulo y necesitan las clases ya definidas."""
        decl = [d for d in self.declaraciones.values() if d]
        literales = [d for d in decl if " = Literal[" in d.split("\n")[0]]
        clases = [d for d in decl if d.startswith("class ")]
        resto = [d for d in decl if d not in literales and d not in clases]
        return "\n\n".join(literales + clases + resto)

    def cabecera(self) -> str:
        huella = hashlib.sha256(json.dumps(self.spec, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()[:12]
        return (
            f"# Generado por scripts/generate_models.py desde el OpenAPI de la API ({self.spec['info']['version']}, {huella}).\n"
            "# No editar a mano: `python scripts/generate_models.py` (con --fetch trae el vivo)."
        )


# --- Utilidades ------------------------------------------------------------------------------


def acepta_null(e: Dict[str, Any]) -> bool:
    t = e.get("type")
    return t == "null" or (isinstance(t, list) and "null" in t) or any(acepta_null(x) for x in e.get("anyOf", []) + e.get("oneOf", []))


def pascal(s: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in re.split(r"[_\-\s.]+", s) if p)


def identificador(s: str) -> bool:
    return s.isidentifier() and not keyword.iskeyword(s)


def juntar(tipos: List[str]) -> str:
    unicos: List[str] = []
    for t in tipos:
        if t not in unicos:
            unicos.append(t)
    sin_none = [t for t in unicos if t != "None"]
    if len(sin_none) == len(unicos):
        return unicos[0] if len(unicos) == 1 else f"Union[{', '.join(unicos)}]"
    if not sin_none:
        return "None"
    interior = sin_none[0] if len(sin_none) == 1 else f"Union[{', '.join(sin_none)}]"
    return f"Optional[{interior}]"


def limites(e: Dict[str, Any]) -> str:
    partes: List[str] = []
    base = next((x for x in e.get("anyOf", []) if x.get("type") in ("integer", "array")), e)
    if base.get("type") == "array":
        mn, mx, unidad = base.get("minItems"), base.get("maxItems"), " items"
    else:
        mn, mx, unidad = base.get("minimum"), base.get("maximum"), ""
    if mx is not None and mx >= 1e15:
        mx = None
    if mn is not None and mx is not None:
        partes.append(f"{mn}–{mx}{unidad}.")
    elif mn is not None:
        partes.append(f"At least {mn}{unidad}.")
    elif mx is not None:
        partes.append(f"At most {mx}{unidad}.")
    d = e.get("default")
    if "default" in e and d is not None and d != {}:
        partes.append(f"Defaults to ``{json.dumps(d)}``.")
    return " ".join(partes)


def docstring(texto: str, sangria: int) -> str:
    texto = texto.replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return f'"""{texto}"""'


def docstring_suelto(texto: Optional[str]) -> str:
    return f"{docstring(texto, 0)}\n" if texto else ""


def leer(origen: str) -> str:
    if re.match(r"^https?://", origen):
        with urllib.request.urlopen(urllib.request.Request(origen, headers={"Accept": "application/json"}), timeout=30) as r:
            return r.read().decode("utf-8")
    return Path(origen).read_text(encoding="utf-8")


def main() -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--fetch", action="store_true")
    a.add_argument("--from", dest="origen")
    a.add_argument("--check", action="store_true")
    args = a.parse_args()

    if args.fetch:
        texto = json.dumps(json.loads(leer(VIVO)), indent=2, ensure_ascii=False) + "\n"
        COPIA.write_text(texto, encoding="utf-8")
    else:
        texto = leer(args.origen or str(COPIA))
    spec = json.loads(texto)

    g = Generador(spec)
    salidas = {MODELOS: g.modelos(), PARAMETROS: g.parametros()}
    faltan = [c for c in g.esquemas if c not in RESPUESTAS and c not in OPCIONES and not es_json(c)]
    if faltan:
        g.avisos.append(f"Componentes nuevos sin generar (sumalos a RESPUESTAS u OPCIONES): {', '.join(faltan)}")

    if args.check:
        viejos = [p.name for p, t in salidas.items() if not p.exists() or p.read_text(encoding="utf-8") != t]
        if viejos:
            print(
                f"{', '.join(viejos)} no están al día con openapi/openapi.json: corré `python scripts/generate_models.py`.", file=sys.stderr
            )
            return 1
        print("_models.py y _params.py al día.")
    else:
        for p, t in salidas.items():
            p.write_text(t, encoding="utf-8")
        print(f"_models.py y _params.py desde el OpenAPI {spec['info']['version']}.")
    for aviso in g.avisos:
        print(f"aviso: {aviso}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
