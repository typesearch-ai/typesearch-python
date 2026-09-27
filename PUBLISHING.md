# Publishing to PyPI

English summary of [PUBLICAR.md](PUBLICAR.md).

`.github/workflows/release.yml` publishes with trusted publishing (OIDC); no token is stored.

1. **Once:** add a GitHub *pending publisher* on PyPI and TestPyPI — project `typesearch`, owner
   `typesearch-ai`, repository `typesearch-python`, workflow `release.yml`, environment `pypi` (PyPI) or
   `testpypi` (TestPyPI) — and create both environments in the repository settings.
2. **Test:** Actions → Release → Run workflow → `testpypi`.
3. **Release:** bump `src/typesearch/_version.py`, date the `CHANGELOG.md` entry, merge to `main`, then
   publish a GitHub release tagged `vX.Y.Z`. The workflow fails if the tag does not match the version.
