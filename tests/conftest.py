from __future__ import annotations

from typing import AsyncIterator, Iterator

import pytest

from typesearch import AsyncTypesearch, Typesearch

from .fake_api import KEY, FakeApi


@pytest.fixture(scope="session")
def fake_api() -> Iterator[FakeApi]:
    api = FakeApi()
    yield api
    api.close()


@pytest.fixture
def api(fake_api: FakeApi) -> Iterator[FakeApi]:
    fake_api.reset()
    yield fake_api
    fake_api.reset()


@pytest.fixture
def ts(api: FakeApi) -> Iterator[Typesearch]:
    with Typesearch(KEY, base_url=api.url) as client:
        yield client


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def ats(api: FakeApi) -> AsyncIterator[AsyncTypesearch]:
    async with AsyncTypesearch(KEY, base_url=api.url) as client:
        yield client
