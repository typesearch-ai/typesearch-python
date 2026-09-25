"""Request and response types of the typesearch API (v1).

Most of them are generated from the API's OpenAPI document, so field names and descriptions match the HTTP
API exactly (snake_case): https://typesearch.ai/docs/api-reference

- Responses are pydantic models. They are built without validation and keep the fields they do not know, so
  a newer API never breaks an older SDK; ``model_dump()`` gives you the JSON back.
- Options are ``TypedDict`` s: type checkers and editors know every keyword argument of every method.
"""

from ._models import *  # noqa: F403
from ._models import __all__ as _models_all
from ._params import *  # noqa: F403
from ._params import __all__ as _params_all
from ._streaming import PartialEvent, ResultEvent, SearchStreamEvent, Step, StepEvent  # noqa: F401

SimilarResponse = SearchResponse  # noqa: F405
"""The response of ``similar()``: a search response with ``object="similar"`` and ``reference`` set."""

SiteSearchResponse = SearchResponse  # noqa: F405
"""The result of a live site search: a search response with ``object="site_search"`` and ``site`` set."""

__all__ = sorted(
    {
        *_models_all,
        *_params_all,
        "PartialEvent",
        "ResultEvent",
        "SearchStreamEvent",
        "SimilarResponse",
        "SiteSearchResponse",
        "Step",
        "StepEvent",
    }
)
