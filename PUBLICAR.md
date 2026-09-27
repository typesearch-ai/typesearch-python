# Publicar en PyPI

`.github/workflows/release.yml` publica con trusted publishing (OIDC): no hay tokens guardados.

## 1. Configurar el publisher (una sola vez)

En PyPI (<https://pypi.org/manage/account/publishing/>) y en TestPyPI
(<https://test.pypi.org/manage/account/publishing/>), agrega un *pending publisher* de GitHub
(funciona antes de que el proyecto exista):

| Campo | PyPI | TestPyPI |
| --- | --- | --- |
| PyPI project name | `typesearch` | `typesearch` |
| Owner | `typesearch-ai` | `typesearch-ai` |
| Repository name | `typesearch-python` | `typesearch-python` |
| Workflow name | `release.yml` | `release.yml` |
| Environment name | `pypi` | `testpypi` |

En GitHub, crea los environments `pypi` y `testpypi` (Settings → Environments). A `pypi` conviene
agregarle revisores obligatorios.

## 2. Probar en TestPyPI

Actions → **Release** → **Run workflow** → `repository: testpypi`. Luego:

```bash
pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ typesearch
```

TestPyPI no acepta subir dos veces la misma versión: para repetir la prueba, sube la versión (por
ejemplo `0.1.1.dev1`) en una rama.

## 3. Publicar una versión

1. Sube la versión en `src/typesearch/_version.py` (`__version__ = "X.Y.Z"`).
2. En `CHANGELOG.md`, cambia `## [X.Y.Z] - Unreleased` por la fecha (`YYYY-MM-DD`) y agrega el enlace
   `[X.Y.Z]: …/releases/tag/vX.Y.Z` al pie.
3. PR contra `main`, CI en verde, merge.
4. En GitHub, crea un release con el tag `vX.Y.Z` sobre `main` y publícalo. El workflow verifica que el
   tag coincida con `_version.py` (si no, falla antes de construir), corre lint, tipos y tests, construye
   y publica en PyPI.
