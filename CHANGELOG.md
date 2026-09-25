# Changelog

All notable changes to `typesearch` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - Unreleased

First release.

- `Typesearch` and `AsyncTypesearch` clients for every endpoint of the typesearch API v1: `search`,
  `search_stream`, `similar`, `contents`, `site_search`, `site_search_and_wait`, `site_search_stream`,
  `jobs.get`, `jobs.wait`, `sources` and `usage`.
- Response models (pydantic) and typed keyword arguments (`TypedDict`) generated from the API's OpenAPI
  document. Responses are built without validation and keep unknown fields, so a newer API never breaks
  this version.
- Automatic retries with exponential backoff and jitter for connection errors, timeouts, `429 rate_limited`
  and `5xx`, honouring `Retry-After`; `quota_exceeded` is never retried.
- Per-call `timeout`, `max_retries` and `extra_headers`.
- Typed errors: `APIError` and its subclasses by status, `APIConnectionError`, `APITimeoutError`,
  `JobFailedError`.
