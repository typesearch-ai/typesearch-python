"""Construye los modelos de respuesta sin validarlos.

Una API más nueva que el SDK puede sumar campos, valores de una enumeración o tipos de pregunta: validar
con pydantic haría fallar el código de quien usa el SDK por algo que no le importa. Acá se arma cada modelo
siguiendo sus anotaciones, se guarda lo desconocido (``extra="allow"``) y lo que falta queda en ``None``.
Es lo mismo que hacen los SDKs de OpenAI y Anthropic.
"""

from __future__ import annotations

import sys
import typing
from typing import Any, Dict, List, Mapping, Tuple, Type, TypeVar, Union

import typing_extensions
from pydantic import BaseModel
from typing_extensions import get_args, get_origin

if sys.version_info >= (3, 10):
    from types import UnionType

    _UNIONS: Tuple[Any, ...] = (Union, UnionType)
else:  # pragma: no cover - Python 3.9
    _UNIONS = (Union,)

_LITERALS = {typing.Literal, typing_extensions.Literal}

M = TypeVar("M", bound=BaseModel)


def construct(model: Type[M], data: Any) -> M:
    """Un modelo a partir del JSON de la API, sin validar. Si ``data`` no es un objeto, un modelo vacío."""
    if not isinstance(data, Mapping):
        data = {}
    fields: Dict[str, Any] = {}
    known = set()
    for name, field in model.model_fields.items():
        key = field.alias or name
        known.add(key)
        fields[name] = _value(field.annotation, data[key]) if key in data else None
    # Lo que el modelo no conoce queda en __pydantic_extra__: accesible como atributo (``r.new_field``) y en
    # ``model_dump()``.
    extra = {k: v for k, v in data.items() if k not in known and isinstance(k, str)}
    fields_set = {n for n, f in model.model_fields.items() if (f.alias or n) in data}
    return model.model_construct(fields_set, **fields, **extra)


def _value(annotation: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(annotation)
    if origin in _UNIONS:
        return _union(get_args(annotation), value)
    if origin in _LITERALS:
        return value
    if origin in (list, List) and isinstance(value, list):
        (item,) = get_args(annotation) or (Any,)
        return [_value(item, v) for v in value]
    if origin in (dict, Dict) and isinstance(value, Mapping):
        args = get_args(annotation)
        item = args[1] if len(args) == 2 else Any
        return {k: _value(item, v) for k, v in value.items()}
    if isinstance(annotation, type) and issubclass(annotation, BaseModel) and isinstance(value, Mapping):
        return construct(annotation, value)
    return value


def _union(options: Tuple[Any, ...], value: Any) -> Any:
    options = tuple(o for o in options if o is not type(None))
    if isinstance(value, Mapping):
        models = [o for o in options if isinstance(o, type) and issubclass(o, BaseModel)]
        if models:
            return construct(_pick(models, value), value)
    if isinstance(value, list):
        for o in options:
            if get_origin(o) in (list, List):
                return _value(o, value)
    return value


def _pick(models: List[Type[BaseModel]], value: Mapping[str, Any]) -> Type[BaseModel]:
    """La variante cuyos campos literales coinciden con el valor (``type: "choice"``…); si no, la primera."""
    for model in models:
        literals = {(f.alias or n): get_args(f.annotation) for n, f in model.model_fields.items() if get_origin(f.annotation) in _LITERALS}
        if literals and all(key in value and value[key] in allowed for key, allowed in literals.items()):
            return model
    return models[0]
