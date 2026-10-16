# CHANGELOG


## v0.0.3 (2026-10-16)

### Bug Fixes

- **deps**: Declare six explicitly now that feedgenerator 2.x dropped it
  ([`2e36a91`](https://github.com/ashcoft/pol/commit/2e36a91be11036319bb621b818fe2e54adb8ab68))

feedgenerator 1.9.2 depended on six and pytz, so 'import six' worked even though it was never
  declared. feedgenerator 2.2.1 depends on neither, so the upgrade removed six from the environment
  and both failing jobs died with:

pol/server.py:11: ModuleNotFoundError: No module named 'six'

* Python tests -> tests/test_ci.py::test_server_module_imports * Docker image build -> 'Verify app
  imports inside image'

pol/server.py and pol/feed.py import six directly (six.PY2/six.PY3, six.moves.urllib.parse,
  six.string_types), so it is a real direct dependency and belongs in requirements.txt. pytz is not
  imported anywhere in the codebase, so it needs no replacement. The rest of the feedgenerator API
  used here (Rss201rev2Feed, Enclosure, add_item, writeString) is unchanged in 2.2.1.

### Documentation

- Note Python 3.15 as the version used by CI and Docker
  ([`a48dfb2`](https://github.com/ashcoft/pol/commit/a48dfb2a1637531f2f9491dcfdda140d61852f3c))

The Dockerfile and CI workflows target Python 3.15 after this upgrade, so keep the documented
  requirement in sync. This also refreshes the pull request so GitHub re-runs CI against the current
  main, where lxml is pinned to 6.1.3 (cp315 wheels exist) instead of 6.1.0 (source build, which
  failed the lint job on Python 3.15).


## v0.0.2 (2026-09-23)

### Bug Fixes

- **pages**: Replace dangling settings.py symlink with a facade module
  ([`f16e047`](https://github.com/ashcoft/pol/commit/f16e047cddb7a03ca7e3623dc6c5ed40bf7ba581))

The repo-root settings.py was a tracked symlink (mode 120000) to frontend/frontend/settings.py,
  which is git-ignored. On a fresh checkout the target does not exist, so the symlink dangled.
  Anything that resolves or archives every path in the tree failed on it:

github-pages 232 | Error: No such file or directory @ rb_check_realpath_internal -
  /github/workspace/settings.py

Jekyll's EntryFilter calls realpath on every entry, and the Pages archive step runs tar
  --dereference, which both abort on a dangling link.

Replace the symlink with a small tracked facade module that re-exports the generated settings, so
  the tree contains no dangling path. The downloader core still does 'from settings import ...' at
  the repo root as before.

.gitignore now ignores only the generated frontend/frontend/settings.py.

Co-authored-by: openhands <openhands@all-hands.dev>

### Chores

- Rename default branch master -> main
  ([`13d3e93`](https://github.com/ashcoft/pol/commit/13d3e933b9f0b7f5f923fb33f25c27c6ac8cf730))

Co-authored-by: openhands <openhands@all-hands.dev>

### Documentation

- Update readme for current repo layout and usage
  ([`9ec325f`](https://github.com/ashcoft/pol/commit/9ec325f1a783935a1035be93819b9c34b9edc437))

Co-authored-by: openhands <openhands@all-hands.dev>


## v0.0.1 (2026-09-06)

### Bug Fixes

- Requirements.txt to reduce vulnerabilities
  ([`974504f`](https://github.com/ashcoft/pol/commit/974504f0c0a6f4387ebe0a14582ef664e2b588d2))

The following vulnerabilities are fixed by pinning transitive dependencies: -
  https://snyk.io/vuln/SNYK-PYTHON-BROTLI-13821834 -
  https://snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-15263096 -
  https://snyk.io/vuln/SNYK-PYTHON-DJANGO-40359 - https://snyk.io/vuln/SNYK-PYTHON-LXML-1047474 -
  https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639 - https://snyk.io/vuln/SNYK-PYTHON-SCRAPY-2414471
  - https://snyk.io/vuln/SNYK-PYTHON-SETUPTOOLS-7448482 -
  https://snyk.io/vuln/SNYK-PYTHON-SQLPARSE-5426157 - https://snyk.io/vuln/SNYK-PYTHON-ZIPP-7430899

- Requirements.txt to reduce vulnerabilities
  ([`8904cfe`](https://github.com/ashcoft/pol/commit/8904cfe677098f886be26b7bb36aaa8e20e3d243))

The following vulnerabilities are fixed by pinning transitive dependencies: -
  https://snyk.io/vuln/SNYK-PYTHON-BROTLI-13821834 -
  https://snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-15263096 -
  https://snyk.io/vuln/SNYK-PYTHON-DJANGO-40359 - https://snyk.io/vuln/SNYK-PYTHON-LXML-1047474 -
  https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639 - https://snyk.io/vuln/SNYK-PYTHON-SCRAPY-2414471
  - https://snyk.io/vuln/SNYK-PYTHON-SETUPTOOLS-7448482 -
  https://snyk.io/vuln/SNYK-PYTHON-SQLPARSE-5426157 - https://snyk.io/vuln/SNYK-PYTHON-ZIPP-7430899

- Requirements.txt to reduce vulnerabilities
  ([`40b49a8`](https://github.com/ashcoft/pol/commit/40b49a8f2492fa57e92c3900e485f75753107b2e))

The following vulnerabilities are fixed by pinning transitive dependencies: -
  https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639 -
  https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15674561

- Requirements.txt to reduce vulnerabilities
  ([`6c0877b`](https://github.com/ashcoft/pol/commit/6c0877b1dd21c35a4b450e1959e942a12f7421a7))

The following vulnerabilities are fixed by pinning transitive dependencies: -
  https://snyk.io/vuln/SNYK-PYTHON-BROTLI-1925013 -
  https://snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-15263096 -
  https://snyk.io/vuln/SNYK-PYTHON-DJANGO-40359 - https://snyk.io/vuln/SNYK-PYTHON-IDNA-16769942 -
  https://snyk.io/vuln/SNYK-PYTHON-LXML-72651 - https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639 -
  https://snyk.io/vuln/SNYK-PYTHON-PYOPENSSL-15674458 -
  https://snyk.io/vuln/SNYK-PYTHON-PYOPENSSL-15674459 -
  https://snyk.io/vuln/SNYK-PYTHON-SCRAPY-1729576 -
  https://snyk.io/vuln/SNYK-PYTHON-SETUPTOOLS-3180412 -
  https://snyk.io/vuln/SNYK-PYTHON-SQLPARSE-1584201 -
  https://snyk.io/vuln/SNYK-PYTHON-TWISTED-6036202 - https://snyk.io/vuln/SNYK-PYTHON-ZIPP-7430899
