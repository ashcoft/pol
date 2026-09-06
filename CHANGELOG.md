# CHANGELOG

## v0.0.1 (2026-09-06)

### Fix

* fix: requirements.txt to reduce vulnerabilities


The following vulnerabilities are fixed by pinning transitive dependencies:
- https://snyk.io/vuln/SNYK-PYTHON-BROTLI-13821834
- https://snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-15263096
- https://snyk.io/vuln/SNYK-PYTHON-DJANGO-40359
- https://snyk.io/vuln/SNYK-PYTHON-LXML-1047474
- https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639
- https://snyk.io/vuln/SNYK-PYTHON-SCRAPY-2414471
- https://snyk.io/vuln/SNYK-PYTHON-SETUPTOOLS-7448482
- https://snyk.io/vuln/SNYK-PYTHON-SQLPARSE-5426157
- https://snyk.io/vuln/SNYK-PYTHON-ZIPP-7430899 ([`974504f`](https://github.com/ashcoft/pol/commit/974504f0c0a6f4387ebe0a14582ef664e2b588d2))

* fix: requirements.txt to reduce vulnerabilities


The following vulnerabilities are fixed by pinning transitive dependencies:
- https://snyk.io/vuln/SNYK-PYTHON-BROTLI-13821834
- https://snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-15263096
- https://snyk.io/vuln/SNYK-PYTHON-DJANGO-40359
- https://snyk.io/vuln/SNYK-PYTHON-LXML-1047474
- https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639
- https://snyk.io/vuln/SNYK-PYTHON-SCRAPY-2414471
- https://snyk.io/vuln/SNYK-PYTHON-SETUPTOOLS-7448482
- https://snyk.io/vuln/SNYK-PYTHON-SQLPARSE-5426157
- https://snyk.io/vuln/SNYK-PYTHON-ZIPP-7430899 ([`8904cfe`](https://github.com/ashcoft/pol/commit/8904cfe677098f886be26b7bb36aaa8e20e3d243))

* fix: requirements.txt to reduce vulnerabilities


The following vulnerabilities are fixed by pinning transitive dependencies:
- https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639
- https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15674561 ([`40b49a8`](https://github.com/ashcoft/pol/commit/40b49a8f2492fa57e92c3900e485f75753107b2e))

* fix: requirements.txt to reduce vulnerabilities


The following vulnerabilities are fixed by pinning transitive dependencies:
- https://snyk.io/vuln/SNYK-PYTHON-BROTLI-1925013
- https://snyk.io/vuln/SNYK-PYTHON-CRYPTOGRAPHY-15263096
- https://snyk.io/vuln/SNYK-PYTHON-DJANGO-40359
- https://snyk.io/vuln/SNYK-PYTHON-IDNA-16769942
- https://snyk.io/vuln/SNYK-PYTHON-LXML-72651
- https://snyk.io/vuln/SNYK-PYTHON-PYASN1-15032639
- https://snyk.io/vuln/SNYK-PYTHON-PYOPENSSL-15674458
- https://snyk.io/vuln/SNYK-PYTHON-PYOPENSSL-15674459
- https://snyk.io/vuln/SNYK-PYTHON-SCRAPY-1729576
- https://snyk.io/vuln/SNYK-PYTHON-SETUPTOOLS-3180412
- https://snyk.io/vuln/SNYK-PYTHON-SQLPARSE-1584201
- https://snyk.io/vuln/SNYK-PYTHON-TWISTED-6036202
- https://snyk.io/vuln/SNYK-PYTHON-ZIPP-7430899 ([`6c0877b`](https://github.com/ashcoft/pol/commit/6c0877b1dd21c35a4b450e1959e942a12f7421a7))

### Unknown

* Fix semantic-release config: use angular commit parser (#27)

The Release workflow has failed on every merge because the pinned
python-semantic-release v9.8.8 does not have a &#39;conventional&#39; commit
parser (known parsers: angular, emoji, scipy, tag); &#39;conventional&#39; is
v10+ syntax, so config validation fails with the unpack error and no
release is ever created. Switch to the v9 angular parser, which handles
conventional-style feat/fix/breaking commits identically.

Validated: RawConfig.model_validate passes with v9.8.8.

Co-authored-by: dependabot[bot] &lt;49699333+dependabot[bot]@users.noreply.github.com&gt;
Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`e80c84d`](https://github.com/ashcoft/pol/commit/e80c84d44ce228143614a34576805b45ce909ef8))

* Merge pull request #25 from ashcoft/dependabot/pip/pip-7e5ff7b710

Bump the pip group across 1 directory with 2 updates ([`a65051e`](https://github.com/ashcoft/pol/commit/a65051ef554feb61a9f90965a7d9258d3aa045f5))

* Bump the pip group across 1 directory with 2 updates

Bumps the pip group with 2 updates in the / directory: [scrapy](https://github.com/scrapy/scrapy) and [sqlparse](https://github.com/andialbrecht/sqlparse).


Updates `scrapy` from 2.16.0 to 2.17.0
- [Release notes](https://github.com/scrapy/scrapy/releases)
- [Changelog](https://github.com/scrapy/scrapy/blob/master/docs/news.rst)
- [Commits](https://github.com/scrapy/scrapy/compare/2.16.0...2.17.0)

Updates `sqlparse` from 0.5.4 to 0.6.0
- [Changelog](https://github.com/andialbrecht/sqlparse/blob/master/CHANGELOG)
- [Commits](https://github.com/andialbrecht/sqlparse/compare/0.5.4...0.6.0)

---
updated-dependencies:
- dependency-name: scrapy
  dependency-version: 2.17.0
  dependency-type: direct:production
  dependency-group: pip
- dependency-name: sqlparse
  dependency-version: 0.6.0
  dependency-type: direct:production
  dependency-group: pip
...

Signed-off-by: dependabot[bot] &lt;support@github.com&gt; ([`f373c96`](https://github.com/ashcoft/pol/commit/f373c9660200099fb1d7f5577bcb5fe80d37c2a6))

* Merge pull request #24 from ashcoft/alert-autofix-19

Potential fix for code scanning alert no. 19: Information exposure through an exception ([`4bf4445`](https://github.com/ashcoft/pol/commit/4bf44456f40d5dad29e949d84e7e9233000ab7d2))

* Potential fix for code scanning alert no. 19: Information exposure through an exception

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`a8e4f11`](https://github.com/ashcoft/pol/commit/a8e4f1192a21b24906cdb8258231ee93137550c5))

* Merge pull request #23 from ashcoft/alert-autofix-16

Potential fix for code scanning alert no. 16: Useless regular-expression character escape ([`16888d3`](https://github.com/ashcoft/pol/commit/16888d342e4a2d4ec9a2bc74993de769b8519769))

* Potential fix for code scanning alert no. 16: Useless regular-expression character escape

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`330332d`](https://github.com/ashcoft/pol/commit/330332d930b6148757a93adb47d2095e624dfec3))

* Merge pull request #22 from ashcoft/alert-autofix-15

Potential fix for code scanning alert no. 15: Useless regular-expression character escape ([`101c5a7`](https://github.com/ashcoft/pol/commit/101c5a723c7632e0ec5763e7ce4163f83fe4fe11))

* Potential fix for code scanning alert no. 15: Useless regular-expression character escape

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`12f6433`](https://github.com/ashcoft/pol/commit/12f6433bd405ac98a17694d44d9d61c8cd0c529c))

* Merge pull request #21 from ashcoft/alert-autofix-21

Potential fix for code scanning alert no. 21: Uncontrolled data used in path expression ([`044c60e`](https://github.com/ashcoft/pol/commit/044c60eb6c59ffa0d2c5578108d9ac06982068d8))

* Use full sha256 hexdigest for cache filename keys

Drop the [:32] truncation of the sha256 cache-key hash to keep full
256-bit collision resistance (cache filename format change is fine: no
in-repo writer depends on the old format). The app is Linux-only
(Docker/ubuntu), so O_NOFOLLOW is available; the getattr fallback covers
other POSIX platforms where it may be absent.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`ceac311`](https://github.com/ashcoft/pol/commit/ceac311bd75d25001f83c8bfe0d37bdf405a4290))

* Use sha256 for cache filename keys instead of md5

Codacy flags md5 as an insecure digest even when used only as a cache
filename key. Switch the cache-key hashes (tryLocalPage and _saveResponse)
to sha256 truncated to 32 hex chars, preserving the existing filename
width and behavior. No security-sensitive hashing is involved.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`fdb4534`](https://github.com/ashcoft/pol/commit/fdb4534c7b59d8c0767957f29c934d9f8b4a58fc))

* Mark the cache-key MD5 as non-security (usedforsecurity=False)

Codacy flagged the md5() call as an insecure hash. The digest here is only
a cache filename key, not a security primitive; usedforsecurity=False
(requires-python &gt;=3.9) documents that intent and clears the scanner
warnings while keeping behavior identical.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`b31e8c7`](https://github.com/ashcoft/pol/commit/b31e8c7acca2cdcbe39304b44815792e2b1a7a0d))

* Handle bytes URLs, root prefetch_dir, and fd lifecycle in cache read

Review findings on the previous commit:

- render_GET passes request.args[b&#39;url&#39;][0] (bytes) into tryLocalPage;
  decode to str first so md5/urlparse/re.sub all work on py3
- boundary now uses base_dir.rstrip(os.path.sep) + sep so a root
  prefetch_dir (/) does not reject every cache file
- os.open/fstat/fdopen are wrapped with try/finally so the descriptor
  cannot leak if fstat or fdopen fails

Verified: bytes and str URLs stay confined to prefetch_dir; root-dir
prefetch works; traversal/absolute inputs still rejected.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`54ab233`](https://github.com/ashcoft/pol/commit/54ab23341f5aa2e94672f548b332ca24cccb3c1f))

* Harden cache read against TOCTOU symlink race

Open the cache file via os.open with O_NOFOLLOW (no symlink follow) and require a regular file via fstat before pickle.load, closing the validate-then-open race flagged by review. Falls back to live fetch on any failure.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`80f9b44`](https://github.com/ashcoft/pol/commit/80f9b44b6316f92e9bc84a6cf37328c1c00b1fcf))

* Fix path injection containment robustly (CodeQL alert 21/22)

Replace commonpath check (vulnerable to prefix-collision like /cache vs /cache-evil) with startswith(base_dir + os.sep) after realpath, and drop the bytes/str type bug in re.sub by using a string pattern. Verified: py_compile, pytest, attack URLs confined to prefetch_dir.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`f7f8c8f`](https://github.com/ashcoft/pol/commit/f7f8c8ffa01fac311c4010e390ba688da026618c))

* Potential fix for code scanning alert no. 21: Uncontrolled data used in path expression

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`aac2de4`](https://github.com/ashcoft/pol/commit/aac2de4d18ed7a9110a8eb2d4e4ff78367249061))

* Merge pull request #20 from ashcoft/alert-autofix-12-1

Potential fix for code scanning alert no. 12: DOM text reinterpreted as HTML ([`a643633`](https://github.com/ashcoft/pol/commit/a643633d1d4a4aa98b9e60048ad61f279e704f0f))

* Potential fix for code scanning alert no. 12: DOM text reinterpreted as HTML

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`013abaf`](https://github.com/ashcoft/pol/commit/013abaf05339f12fc00f48925d7c01fa9e0ba8b3))

* Merge pull request #19 from ashcoft/alert-autofix-18

Potential fix for code scanning alert no. 18: Uncontrolled data used in path expression ([`4debf1b`](https://github.com/ashcoft/pol/commit/4debf1b400e96f750b58e5a143e2b87636419f37))

* Potential fix for code scanning alert no. 18: Uncontrolled data used in path expression

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`6c6b521`](https://github.com/ashcoft/pol/commit/6c6b521aadee8bff0de3e5f5b28e7fc9e505d92f))

* Merge pull request #18 from ashcoft/alert-autofix-13

Potential fix for code scanning alert no. 13: DOM text reinterpreted as HTML ([`f46f1ab`](https://github.com/ashcoft/pol/commit/f46f1ab22ed16ac514a5bb8a71ddcc92f315d3e1))

* Potential fix for code scanning alert no. 13: DOM text reinterpreted as HTML

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`cd73c68`](https://github.com/ashcoft/pol/commit/cd73c68c672ae31ecc6cb9c88722ab304c586b04))

* Merge pull request #17 from ashcoft/alert-autofix-10

Potential fix for code scanning alert no. 10: DOM text reinterpreted as HTML ([`e31efc5`](https://github.com/ashcoft/pol/commit/e31efc5ff18ebc9c15ecdf87f68f06a342aa27d8))

* Potential fix for code scanning alert no. 10: DOM text reinterpreted as HTML

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`4cf9a40`](https://github.com/ashcoft/pol/commit/4cf9a4020ee85ee5259d6d9ca8d903d39a0a3efe))

* Merge pull request #16 from ashcoft/add-ci-and-release-workflows

Add test/docker CI and semantic-release workflows ([`c089e4e`](https://github.com/ashcoft/pol/commit/c089e4ebe02142e299b35341cbdc5c9826a298c6))

* Exclude tests dir from Codacy assert-usage false positives

The remaining Codacy findings are all the style rule flagging `assert` in pytest files (asserts are removed under -O, but tests deliberately use them and pytest is never run with -O). Exclude tests/ via .codacy.yaml.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`c635402`](https://github.com/ashcoft/pol/commit/c635402be9a61af66ca5113be2d9ee3e28cc3222))

* Gate release workflow on successful CI run

Release now triggers on CI workflow_run completion (success only) instead of raw push, so a release is never published from a commit whose tests/docker failed.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`74c193d`](https://github.com/ashcoft/pol/commit/74c193d0420bbc245cac309308ecbb3c2a426f71))

* Address review feedback: docker hardening, release config, tests, action pinning

- Dockerfile: run as non-root appuser; align EXPOSE/CMD with the downloader port (1234)
- pyproject.toml: static version + version_variables for python-semantic-release (fixes version_toml vs dynamic mismatch)
- tests/test_ci.py: assert real behavior (inside-path must not raise; valid-name extraction produces empty result for non-matching xpath)
- ci.yml/release.yml: pin third-party actions to full commit SHAs (supply-chain hardening)

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`7f0c524`](https://github.com/ashcoft/pol/commit/7f0c5248f91913c9e7912220a093cf01f74035f0))

* Fix real py3 bugs found by pylint; add lint job

- pol/server.py: urlparse was undefined -&gt; six.moves.urllib.parse.urlparse
- pol/feed.py: w3lib.url.urljoin_rfc/urljoin no longer exist -&gt; six.moves.urllib.parse.urljoin
- ci.yml: add lint job (pylint errors-only, non-blocking; node --check on vendored JS)

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`8229065`](https://github.com/ashcoft/pol/commit/8229065c35216736cb5e188e055c24977c131585))

* CI: generate settings.py from example before pytest

pol/feed.py imports the repo-root settings module (symlink to frontend/frontend/settings.py), which is gitignored and not present on the runner. Generate it from settings.py.example in the python-tests job.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`e336877`](https://github.com/ashcoft/pol/commit/e336877d1f85de7483493d7b491adaee20099bb5))

* Fix CI: ignore legacy test_downloader, load docker image into daemon

- pytest.ini ignores tests/test_downloader.py (py2-era manual smoke script that breaks pytest collection on CI: imports settings from repo root)
- docker/build-push-action now uses load:true so the built image is available to docker run for the app-import check

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`9f80024`](https://github.com/ashcoft/pol/commit/9f800246b0e3d973ff4c972fcce6deb58e071697))

* Add CI (python tests + docker build) and semantic-release workflows

CI:
- Python tests job: installs deps on Python 3.11 and runs pytest (tests/test_ci.py) covering pol.server import, pol.log import, and the snapshot path-guard (rejects traversal, accepts valid names)
- Docker job: builds the image with buildx and verifies the app imports inside it

Required fixes to make CI pass:
- pol/server.py: drop DecompressionMiddleware (removed in modern Scrapy; HttpCompressionMiddleware now decompresses)
- pol/server.py: use six.string_types instead of basestring (py3)
- frontend/frontend/setup_tool_ext.py: py3-compat (open in binary, .items() instead of .iteritems(), str(ex) instead of ex.message)
- requirements.txt: w3lib&gt;=2.3.1 (1.17.0 breaks on modern Python re) and pin cssselect==1.2.0 (compat with parsel 1.5.0)
- Dockerfile: modernized to python:3.11-slim so the image builds with current pins

Release:
- python-semantic-release workflow (conventional commits -&gt; GitHub releases) on master
- pyproject.toml + pol.__version__ for versioning

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`3ec2d96`](https://github.com/ashcoft/pol/commit/3ec2d967f90683f339f3bba03acb5d3da9da1790))

* Merge pull request #15 from ashcoft/fix-alert-7-xss-through-dom

Fix DOM text reinterpreted as HTML in Collapse data-api (CodeQL alert #7) ([`d0d36b4`](https://github.com/ashcoft/pol/commit/d0d36b46037d98afbf4090133255281eabd8f178))

* Fix DOM text reinterpreted as HTML in Collapse data-api (CodeQL alert 7)

target comes from data-target/href attributes and was used in $(target) three times; an attacker-controlled value starting with &#34;&lt;&#34; would be parsed as HTML (XSS). Resolve strictly as a CSS selector via $(document).find(target) with try/catch fallback to empty collection, consistent with prior Collapse/Alert/Carousel/Modal fixes (PRs 7, 13, 14). Behavior for valid selectors unchanged.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`f68cdf1`](https://github.com/ashcoft/pol/commit/f68cdf1fac0af99f7c8b28c1d627060666d73880))

* Merge pull request #14 from ashcoft/fix-alert-6-xss-through-dom

Fix DOM text reinterpreted as HTML in Carousel/Modal data-api (CodeQL alert #6) ([`02e9578`](https://github.com/ashcoft/pol/commit/02e9578023d96954516c099d9275cfaf4ff4d9c3))

* Fix DOM text reinterpreted as HTML in Carousel/Modal data-api (CodeQL alert 6)

$target was built with $(attr-derived-string), which parses strings starting with &#34;&lt;&#34; as HTML. An attacker-controlled data-target/href could inject elements (XSS). Resolve strictly as a CSS selector via $(document).find() (never HTML), with try/catch fallback to empty collection. Applied to both the flagged Carousel data-api handler and the identical Modal data-api pattern.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`360c0b1`](https://github.com/ashcoft/pol/commit/360c0b107a1bb4c9261112fc172abdae0680c5cd))

* Merge pull request #13 from ashcoft/fix-alert-5-xss-through-dom

Fix DOM text reinterpreted as HTML in Alert.close (CodeQL alert #5) ([`5da095e`](https://github.com/ashcoft/pol/commit/5da095ef1c467ad136bb933d1b43a0f27fd9d7f8))

* Revert explicit &#34;&lt;&#34; heuristic per review: rely on find() as the security boundary

The &#34;starts with &lt;&#34; check adds no security (find() never parses HTML regardless), is bypassable in spirit (whitespace/escape variants), and diverges from the established Collapse fix pattern. Keep the minimal secure form: $(document).find(selector) + try/catch fallback.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`f978f03`](https://github.com/ashcoft/pol/commit/f978f03244d2e863b86aea9386827ef2414ea716))

* Explicitly reject HTML-like selectors instead of catching all errors

Per review: make the security intent explicit by rejecting selectors starting with &#34;&lt;&#34; up front (never interpret DOM text as HTML), so genuine selector syntax errors are not masked by a blanket catch. Keep the try/catch as a narrow safety net around $(document).find only.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`663f22d`](https://github.com/ashcoft/pol/commit/663f22df6d3669d31da166e80d79072a4d4aaeeb))

* Fix DOM text reinterpreted as HTML in Alert.close (CodeQL alert 5)

selector comes from the data-target/href attribute (DOM text) and was passed to $(selector), which parses strings starting with &#34;&lt;&#34; as HTML — an attacker-controlled attribute could inject elements (XSS). Resolve the string strictly as a CSS selector via $(document).find(selector) (never HTML), with a try/catch fallback to an empty collection for malformed/HTML-like input. Consistent with the Collapse fix in PR7.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`e85ce33`](https://github.com/ashcoft/pol/commit/e85ce3326aaab6932f23b685ba2a3e900249502c))

* Merge pull request #12 from ashcoft/alert-autofix-4

Potential fix for code scanning alert no. 4: Bad HTML filtering regexp ([`1ef72cb`](https://github.com/ashcoft/pol/commit/1ef72cbcf5f9ca3c4dda03238282dbe5075a7e7c))

* Fix rcleanScript to keep CDATA terminator (]]&gt;) intact

The autofix moved &#34;&gt;&#34; into the &#34;--&#34; alternation only, so &#34;]]&gt;&#34; no longer matched and trailing &#34;]]&gt;&#34; reached jQuery.globalEval (SyntaxError). Restore &#34;]]&gt;&#34; as its own alternation branch while accepting both &#34;--&gt;&#34; and &#34;--!&gt;&#34; comment terminators.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`23c83b1`](https://github.com/ashcoft/pol/commit/23c83b1cd8d32d8f58b4785dd1c2d59da062d700))

* Potential fix for code scanning alert no. 4: Bad HTML filtering regexp

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`f83ea8b`](https://github.com/ashcoft/pol/commit/f83ea8b549e043b0185e8abd46c41bae64bb613d))

* Merge pull request #11 from ashcoft/fix-alert-1-path-injection

Fix path injection in snapshot file loading (CodeQL alert #1) ([`2f019ea`](https://github.com/ashcoft/pol/commit/2f019eaabebf79c5eb2fa8abc31fdfcb1f0f1693))

* Harden boundary check and regex anchoring per review

- Use a trailing-separator-stripped boundary prefix so SNAPSHOT_DIR configured as a filesystem root ((/))) still admits files inside it (previously required a double slash prefix and rejected everything)
- Use \Z instead of $ in the snapshot_time regex for strict end-of-string anchoring (Python $ matches before a trailing newline

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`40c8f63`](https://github.com/ashcoft/pol/commit/40c8f6378125f4ade0673c64272e2351e503d02f))

* Fix path traversal in setup_tool_ext (CodeQL alert 1)

snapshot_time is user-controlled and previously joined into a path with only a loosely-anchored regex check (re.match, no end anchor), allowing &#34;.../../../etc/passwd&#34; forms to escape SNAPSHOT_DIR (/tmp). Fix:

- In build_xpath_results, resolve the joined path with os.path.realpath and require it to stay inside the realpath(SNAPSHOT_DIR) (reject traversal/symlink-escape outright)
- Anchor both caller-side snapshot_time regexes with $ so the exact timestamp format is required end-to-end

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`77e6d86`](https://github.com/ashcoft/pol/commit/77e6d8633cd46155f17ad9b502a5237052dcef62))

* Merge pull request #10 from ashcoft/fix-alert-2-xhtml-selfclosing

Fix unsafe self-closing HTML tag expansion (CodeQL alert #2) ([`307b05a`](https://github.com/ashcoft/pol/commit/307b05adf7ac7a76474a32dc97288cff955737fd))

* Fix unsafe self-closing HTML tag expansion (CodeQL alert 2)

Remove the rxhtmlTag-based self-closing-tag expansion from the vendored jQuery 1.11.3 bundle. The regex rewrote any &#34;&lt;.../&gt;&#34;-looking fragment inside the HTML string — including inside quoted attribute values — which could corrupt sanitized input (js/unsafe-html-expansion). jQuery upstream removed this old-IE workaround entirely in 3.5.0; modern browsers parse self-closing tags natively. The two call sites (buildFragment andthe .html( setter fast-path) now insert the original string unchanged, and the now-unused regex declaration is deleted.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`1741152`](https://github.com/ashcoft/pol/commit/17411528a82c5a6c6c11328d92754263b9e2699d))

* Merge pull request #8 from ashcoft/dependabot/pip/pip-d6743723f4

Bump django from 4.2.30 to 5.2.16 in the pip group across 1 directory ([`e390716`](https://github.com/ashcoft/pol/commit/e3907165f249febcff26fc05057332c6571e20a4))

* Bump django from 4.2.30 to 5.2.16 in the pip group across 1 directory

Bumps django from 4.2.30 to 5.2.16 ([`f49e3b8`](https://github.com/ashcoft/pol/commit/f49e3b82dc5350f80c35e1157ab7d67139c8b88e))

* Merge pull request #7 from ashcoft/alert-autofix-14

Potential fix for code scanning alert no. 14: Unsafe jQuery plugin ([`d33f933`](https://github.com/ashcoft/pol/commit/d33f93354bae0820815e4a33eda6ffc18e5e61e0))

* Drop redundant notice when error annotation already fires

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`09076df`](https://github.com/ashcoft/pol/commit/09076dfc9531132fa28d8e09d638b978f865b44e))

* Restore spaces in workflow comment lines

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`e0cc686`](https://github.com/ashcoft/pol/commit/e0cc6865a41a2b2ee9ecae939edceb8fcf8e9227))

* Annotate skipped Snyk scans as error in Actions UI

In addition to the job-level skip, emit an error-level annotation on the token-check step so the skipped security scans are loud and visible in the run UI, with a pointer on how to enable them (SNYK_TOKEN secret). The step still exits 0 so CI is not permanently broken when no token is configured.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`697fd3f`](https://github.com/ashcoft/pol/commit/697fd3fb8d2e0c9cb4797499419a22fc716e0d9a))

* Gate Snyk job on token presence so skipped shows as skipped

When SNYK_TOKEN is absent, the scan job is now skipped at job level (via a cheap snyk-token dependency job) instead of running its steps and reporting success. This makes the absence of scanning explicit in CI (job state: skipped) rather than a false-green security check. SNYK_TOKEN is provided job-scope to the snyk job, so scan steps always have credentials when they run.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`968bba0`](https://github.com/ashcoft/pol/commit/968bba0c2e6fa5b971e650410a953beea4a2f85e))

* Degrade invalid parent selectors to empty collection

When parent is an HTML-like or malformed selector string, jQuery find() throws a SyntaxError from the selector engine, aborting Collapse initialization. Wrap in try/catch and fall back to an empty collection, keeping selector-only semantics while never parsing HTML.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`37bbbe1`](https://github.com/ashcoft/pol/commit/37bbbe1277c8666e674df88ed3a65de536564792))

* Address review feedback

- Provide SNYK_TOKEN to each gated snyk step (fixes scan steps running unauthenticated when a token is configured
- Use $(document).find(parent) for string parents: idiomatic public API, keeps selector-only semantics and drops the semi-private $.find( double- wrap
- Emit a GitHub Actions notice when scans are skipped due to missing SNYK_TOKEN so a green check is distinguishable from a completed scan

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`a4ea40e`](https://github.com/ashcoft/pol/commit/a4ea40e81d897e42b4670de6001df7a0db41dc0a))

* Also skip Docker build when SNYK_TOKEN is unset

The Snyk-workflow &#39;Build a Docker image&#39; step only exists to support Snyk Container scanning; without a token it served no purpose and failed because requirements.txt pins an unavailable Django version.

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`948f79d`](https://github.com/ashcoft/pol/commit/948f79d3e06b791b2c47f0fb143b6502104e8fa5))

* Fix Snyk Security CI failure: skip scans when SNYK_TOKEN is missing

The Snyk job failed with SNYK-0005 (authentication error) because the SNYK_TOKEN secret is not configured in the repository. Add a token check step and gate the Snyk scan/monitor/upload steps on it, so the workflow passes (steps skip) when no token is set

Co-authored-by: openhands &lt;openhands@all-hands.dev&gt; ([`3dedb78`](https://github.com/ashcoft/pol/commit/3dedb7887282d36b7c30da58c490778a4d2dd83f))

* Potential fix for pull request finding &#39;CodeQL / Unsafe jQuery plugin&#39;

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`d5b56d4`](https://github.com/ashcoft/pol/commit/d5b56d42d4d201878b58907ca5efbdbed8c9f346))

* Potential fix for code scanning alert no. 14: Unsafe jQuery plugin

Co-authored-by: Copilot Autofix powered by AI &lt;62310815+github-advanced-security[bot]@users.noreply.github.com&gt; ([`0d641d6`](https://github.com/ashcoft/pol/commit/0d641d62d746198fd41a180213f10817819669f6))

* Update readme.md ([`6c6bd16`](https://github.com/ashcoft/pol/commit/6c6bd1690275ee32ebd3370f63630401fe0e263d))

* Add `pullfrog.yml` workflow ([`fb67e17`](https://github.com/ashcoft/pol/commit/fb67e1799c318c5711cb9a7759a86022ed6c5164))

* Merge pull request #6 from ashcoft/dependabot/pip/pip-0021e3f681

Bump the pip group across 1 directory with 4 updates ([`74cc011`](https://github.com/ashcoft/pol/commit/74cc01164ec22353cf95c49ea88d9f14a6d73654))

* Bump the pip group across 1 directory with 4 updates

Bumps the pip group with 4 updates in the / directory: [django](https://github.com/django/django), [lxml](https://github.com/lxml/lxml), [scrapy](https://github.com/scrapy/scrapy) and [sqlparse](https://github.com/andialbrecht/sqlparse).


Updates `django` from 1.8.6 to 4.2.30
- [Commits](https://github.com/django/django/compare/1.8.6...4.2.30)

Updates `lxml` from 4.4.0 to 6.1.0
- [Release notes](https://github.com/lxml/lxml/releases)
- [Changelog](https://github.com/lxml/lxml/blob/master/CHANGES.txt)
- [Commits](https://github.com/lxml/lxml/compare/lxml-4.4.0...lxml-6.1.0)

Updates `scrapy` from 1.8.2 to 2.16.0
- [Release notes](https://github.com/scrapy/scrapy/releases)
- [Changelog](https://github.com/scrapy/scrapy/blob/master/docs/news.rst)
- [Commits](https://github.com/scrapy/scrapy/compare/1.8.2...2.16.0)

Updates `sqlparse` from 0.4.4 to 0.5.4
- [Changelog](https://github.com/andialbrecht/sqlparse/blob/master/CHANGELOG)
- [Commits](https://github.com/andialbrecht/sqlparse/compare/0.4.4...0.5.4)

---
updated-dependencies:
- dependency-name: django
  dependency-version: 4.2.30
  dependency-type: direct:production
  dependency-group: pip
- dependency-name: lxml
  dependency-version: 6.1.0
  dependency-type: direct:production
  dependency-group: pip
- dependency-name: scrapy
  dependency-version: 2.16.0
  dependency-type: direct:production
  dependency-group: pip
- dependency-name: sqlparse
  dependency-version: 0.5.4
  dependency-type: direct:production
  dependency-group: pip
...

Signed-off-by: dependabot[bot] &lt;support@github.com&gt; ([`ef65954`](https://github.com/ashcoft/pol/commit/ef6595482941c510fc075712c344096533b016dc))

* Merge pull request #3 from ashcoft/snyk-fix-11e86fba2a66369389a4765b5ee48a98

[Snyk] Fix for 9 vulnerabilities ([`1efb210`](https://github.com/ashcoft/pol/commit/1efb2104a71faee039fa45968ba892389ccbea01))

* Create snyk-security.yml ([`08652e2`](https://github.com/ashcoft/pol/commit/08652e210dc77398b736f206d34b216b887fc6d8))

* Merge pull request #4 from taroved/master

pr ([`7ff672e`](https://github.com/ashcoft/pol/commit/7ff672e15bba6742acf164b8698e59b2f29f5cb4))

* Update readme.md ([`2a6e915`](https://github.com/ashcoft/pol/commit/2a6e915468d816c071e74712d061e4ceb07ed24c))

* Update readme.md ([`4fe5319`](https://github.com/ashcoft/pol/commit/4fe531999d379029e30e95b5fd04c6cf009dc8a9))

* Update readme.md ([`ac8a4b3`](https://github.com/ashcoft/pol/commit/ac8a4b30c0c8bfc096d21da17aaa9d21393a86ef))

* Update readme.md ([`3cae446`](https://github.com/ashcoft/pol/commit/3cae4469c21039ec458b8fb9291ef7202d5e06a6))

* Merge pull request #2 from ashcoft/snyk-fix-ca99cf03b6f287fcd36551b37771d486

[Snyk] Security upgrade pyasn1 from 0.5.1 to 0.6.3 ([`3894cc6`](https://github.com/ashcoft/pol/commit/3894cc622b16968957d3dea4347dfd25f0eed254))

* Merge pull request #1 from ashcoft/snyk-fix-b1e4359b6c1fda938c04d91328f5093d

[Snyk] Fix for 13 vulnerabilities ([`2ce855a`](https://github.com/ashcoft/pol/commit/2ce855a0b63d5eb3a45340ad6662256c4ced1d8d))

* Update readme.md ([`1e33abc`](https://github.com/ashcoft/pol/commit/1e33abcad5f6ee0581ff1f22309b1b8f81e76c33))

* Merge pull request #82 from MrJaroslavik/patch-1

Fix shure &gt; sure ([`390e11c`](https://github.com/ashcoft/pol/commit/390e11cc8140dbede11fe1854853bde79025b7eb))

* Fix shure &gt; sure ([`2a9a2e4`](https://github.com/ashcoft/pol/commit/2a9a2e4c74b47a29fa8cd8ccb47efd5c32410d0a))

* python3 ([`898c38c`](https://github.com/ashcoft/pol/commit/898c38c71f52e0a1ac62d82fe28189a414750478))

* sass version update ([`01e63bc`](https://github.com/ashcoft/pol/commit/01e63bc78777ad807c62ca73f567ada70342a502))

* Merge pull request #42 from marlluslustosa/master

fix and add dependencies and path ([`2d8c118`](https://github.com/ashcoft/pol/commit/2d8c118705ab4c629e50af7e81c869f87e5b83e1))

* fix path ([`5381d42`](https://github.com/ashcoft/pol/commit/5381d426b48e7de8741abf302c2c8ef0a59c4757))

* Create settings.py ([`02b0822`](https://github.com/ashcoft/pol/commit/02b0822fc1210acdbfd587f9be176c98fc1d00b1))

* fix path ([`78c7f60`](https://github.com/ashcoft/pol/commit/78c7f60e03774de0d62f88c4762eb3a1307ec469))

* fix path ([`ce781e8`](https://github.com/ashcoft/pol/commit/ce781e837d985ef811426837369e605a1b5efffd))

* fix and add dependencies and path ([`4603342`](https://github.com/ashcoft/pol/commit/4603342beac92623106ff71f82769040f834283f))

* fix and add dependencies and path ([`31864ff`](https://github.com/ashcoft/pol/commit/31864ff7af83fb7dfb4b6703ee35721d176621dd))

* fix and add dependencies and path ([`63c060b`](https://github.com/ashcoft/pol/commit/63c060b8af887ed417405c4ac2d4990f302dd3a6))

* wait-for-it ([`d3cf32c`](https://github.com/ashcoft/pol/commit/d3cf32ce5cdb0b66ea36763506a0b80ce2eb5dc3))

* wait-for-it ([`820af6f`](https://github.com/ashcoft/pol/commit/820af6f9b31f07fa4e52647d1318a1d940704800))

* Merge pull request #40 from marlluslustosa/master

running mysql container ([`21508b7`](https://github.com/ashcoft/pol/commit/21508b74794079cfa143836ad4802e3f12ef8928))

* Update Dockerfile ([`e656026`](https://github.com/ashcoft/pol/commit/e65602626da439ff0b34d0c9bbe06d5def5d1401))

* Update wait-for-it.sh ([`0934fd9`](https://github.com/ashcoft/pol/commit/0934fd977bdf220fb2c842533c12c265acb04659))

* Update docker-compose.yaml ([`aacf265`](https://github.com/ashcoft/pol/commit/aacf2659f298a154fe814697e62632136920ca9b))

* Merge pull request #35 from marlluslustosa/master

wait-for-it.sh edited - ok ([`4533477`](https://github.com/ashcoft/pol/commit/45334778e719631233c3f14936defe4a79ddb09d))

* wait-for-it.sh edited - ok ([`52c447e`](https://github.com/ashcoft/pol/commit/52c447eac0a5790d1c5face02e323ae3b9910363))

* Merge pull request #32 from marlluslustosa/master

Dockerize the project ([`c2a3b1a`](https://github.com/ashcoft/pol/commit/c2a3b1a7c74eba2e14499dd5b8a3fc7a270c6657))

* Update readme.md ([`ad7c787`](https://github.com/ashcoft/pol/commit/ad7c787b984482267b94f9c6dae6dd98aabc21ae))

* Update default.site-example ([`fd5ae48`](https://github.com/ashcoft/pol/commit/fd5ae48fc635a3a49455b4e51b3ed0d9980da893))

* Update start.sh ([`5067a3e`](https://github.com/ashcoft/pol/commit/5067a3efbec6e43a606dd52911fccb31b4b3fdd1))

* Update docker-compose.yaml ([`6290edc`](https://github.com/ashcoft/pol/commit/6290edc399e4f480fcfdba5b2127287cdd35b436))

* Update Dockerfile ([`ccb6b87`](https://github.com/ashcoft/pol/commit/ccb6b871ada896b61fdaeaa04a3e48413b1f4142))

* first commit ([`741b5ec`](https://github.com/ashcoft/pol/commit/741b5ec94696c94f3fc48991e253d829aa60a943))

* Update readme.md ([`ae5cc4f`](https://github.com/ashcoft/pol/commit/ae5cc4f1a9f37aa10842cdf07ea9230872b34986))

* Update readme.md ([`e80786f`](https://github.com/ashcoft/pol/commit/e80786fe51c49da5a05c3251a32a631e78df82f4))

* Update docker-compose.yaml ([`1ea8ab0`](https://github.com/ashcoft/pol/commit/1ea8ab0a4cc8aebccb78f51e33ffcb204caff7ec))

* Create start.sh ([`d027641`](https://github.com/ashcoft/pol/commit/d0276410a8f98f9e62e4c17d00a824b9b619ef2d))

* Create wait-for-it.sh ([`8e066f6`](https://github.com/ashcoft/pol/commit/8e066f6a204836ee16e5de822a665ceb3c91761b))

* Create docker-compose.yaml ([`4bb7de3`](https://github.com/ashcoft/pol/commit/4bb7de37fd44db6d6bdbb88248542a84ce911db4))

* Create Dockerfile ([`e850002`](https://github.com/ashcoft/pol/commit/e850002772240d95d260870c90ecca3549c63f38))

* duplicates ([`f546544`](https://github.com/ashcoft/pol/commit/f5465442f29f36acf0f56d492ca3f2a8cf435bcc))

* fixes ([`79c0bc4`](https://github.com/ashcoft/pol/commit/79c0bc467e4b59f53b93cdcd56f10aabce420c7d))

* encoding problem ([`019c56b`](https://github.com/ashcoft/pol/commit/019c56bb82596022d9da336d7650ececc611f59f))

* unicode url ([`54b840f`](https://github.com/ashcoft/pol/commit/54b840f72ed5db4b95ab258aa9d63dc1dc757c70))

* stats ([`31a5d0f`](https://github.com/ashcoft/pol/commit/31a5d0f048ceb64f3f7bb9ef95ed6ec8148dd2cf))

* disable caching ([`33afd5f`](https://github.com/ashcoft/pol/commit/33afd5f9ce029bbb6f8b23b533265d1fe10e78e9))

* fix mobile ([`0d8ec7a`](https://github.com/ashcoft/pol/commit/0d8ec7a7b5633057c8fd3835562835fb9f1e138e))

* no js ([`698b712`](https://github.com/ashcoft/pol/commit/698b712244bcaa2a2f00bf12cd5e3ffdddb6cc97))

* js ([`334163f`](https://github.com/ashcoft/pol/commit/334163ff07fcbfbff0f00c6a43ceb29de03a68bf))

* readme ([`2c9f191`](https://github.com/ashcoft/pol/commit/2c9f191f5d60dcf37e84e62aa27079b14cf816ea))

* md5 ([`5f8a966`](https://github.com/ashcoft/pol/commit/5f8a9664223a3734150441e6eddb520e0fae21ae))

* reduse db size (1) ([`bc0545a`](https://github.com/ashcoft/pol/commit/bc0545a3c88e092143e27b9dc6b7089634ab72ea))

* reduse db size ([`2abe044`](https://github.com/ashcoft/pol/commit/2abe04457cc9b478375de88163c40508b944d485))

* feed name ([`6d037ba`](https://github.com/ashcoft/pol/commit/6d037ba78484cfe1f90f06854c5e767f2a9a59e3))

* stat attrs ([`f601c0d`](https://github.com/ashcoft/pol/commit/f601c0d5f8bf6be9188e523a3b834888e811ec3b))

* small fixes ([`d903861`](https://github.com/ashcoft/pol/commit/d90386117b24434b287225fae2786909422c2c67))

* sanitize ([`6f97665`](https://github.com/ashcoft/pol/commit/6f97665b68680a266ba55254095e30f73ed507d2))

* sanitize feed preview ([`94b7e53`](https://github.com/ashcoft/pol/commit/94b7e53a404a3112bbd219c197b31cb8d7d9051e))

* feed url ([`d03cbe3`](https://github.com/ashcoft/pol/commit/d03cbe3478fabeddcbbde1b9a10b099a9bc41c43))

* feed url ([`aa5c6e2`](https://github.com/ashcoft/pol/commit/aa5c6e294a1014db2751fe246f09f5594380294d))

* posts data removed ([`b468a66`](https://github.com/ashcoft/pol/commit/b468a6631623c35cb4e2f3d119cb378aa111c8ff))

* feed param ([`04b26b8`](https://github.com/ashcoft/pol/commit/04b26b8eee81e95b56e449ae9c22d6a6e4cbcc7e))

* Update readme.md ([`2613d76`](https://github.com/ashcoft/pol/commit/2613d768a47a27f2fd2a1dbff52740a15ed75077))

* Update readme.md ([`e833af1`](https://github.com/ashcoft/pol/commit/e833af16a852365e01a5691670647be887762b66))

* Update readme.md ([`9bd6662`](https://github.com/ashcoft/pol/commit/9bd6662c5b2e86e68fff3d78efc60e2e5d0ef642))

* attributes ([`6db89fc`](https://github.com/ashcoft/pol/commit/6db89fcbe1952da9ad0934324dc3ed982ea71303))

* log only not traced exceptions ([`e02f4f0`](https://github.com/ashcoft/pol/commit/e02f4f0d1ba7c139b70497605ca67138079c6a9d))

* show not parsed content ([`8e48331`](https://github.com/ashcoft/pol/commit/8e483314d82484400daf66c0db843b6850bff4a7))

* prefetch_dir ([`08b916d`](https://github.com/ashcoft/pol/commit/08b916dc658ad5a1276c93f2e410a7fe0d2e484c))

* pickle ([`bdc115d`](https://github.com/ashcoft/pol/commit/bdc115db2d0abbe98f84fa59e222461ac69a93d6))

* prefetch ([`0385a09`](https://github.com/ashcoft/pol/commit/0385a0900895f16400c78fb4b060ea03b3770752))

* gitignore ([`2f2610f`](https://github.com/ashcoft/pol/commit/2f2610fc2d0f13bba1856b90108aecb74c28dcff))

* assets ([`0824f6b`](https://github.com/ashcoft/pol/commit/0824f6b8c6a721542d44958a4099ce2f305d7a42))

* feed fix ([`0ce333e`](https://github.com/ashcoft/pol/commit/0ce333e5e71d69bf52bfe416d73c552b50e6289b))

* prem ([`a6e75a2`](https://github.com/ashcoft/pol/commit/a6e75a22a38d602d76616fca35e1e37675ed22cc))

* lib start ([`6e9884e`](https://github.com/ashcoft/pol/commit/6e9884e34a2384614671fd57c952fdb466bb3741))

* tests ([`89b9ffb`](https://github.com/ashcoft/pol/commit/89b9ffb78d2fb29b06ed63b4506185f03ebcfe23))

* fix ([`fc4d555`](https://github.com/ashcoft/pol/commit/fc4d5559bd91b6c7cec4f3730dbacf6ee1524514))

* test(2) ([`e8a44d5`](https://github.com/ashcoft/pol/commit/e8a44d5dee081ae2ffcc89ff9fd6cc85093aa521))

* test(1) ([`c6721dc`](https://github.com/ashcoft/pol/commit/c6721dc08d8a79235b08489c9bac6524be012d43))

* test ([`0656dcb`](https://github.com/ashcoft/pol/commit/0656dcb77b30eb83bd8ed8a1d53bc7f3bacb84bb))

* split to modules ([`b3c5898`](https://github.com/ashcoft/pol/commit/b3c58981d01b658b9925a6c74106d1a7dcdd53d6))

* stats ([`fcc773d`](https://github.com/ashcoft/pol/commit/fcc773d434d2eb3c64a8a741d23280bd8d711382))

* stat ([`91a33fe`](https://github.com/ashcoft/pol/commit/91a33febb93ed9c9d8d6a63ab8bb1fc743882d36))

* mon fix ([`ddd9a79`](https://github.com/ashcoft/pol/commit/ddd9a79f22604f47ee50b68ea4fa0c17d1308346))

* new mon ([`6e5cb83`](https://github.com/ashcoft/pol/commit/6e5cb836cd52455b96f5cb8b8d1cc614c00ac5af))

* no sql log ([`35c3825`](https://github.com/ashcoft/pol/commit/35c382553c1b9142a0be075b357a39b292c59464))

* mon lib + mysql fix ([`6aefb2d`](https://github.com/ashcoft/pol/commit/6aefb2dbcd91fb3513c73b512253074075122995))

* leak ([`7454722`](https://github.com/ashcoft/pol/commit/74547224d67f8edf1b375f0dc2df3d12c8b3c075))

* remove debug code ([`9e451d1`](https://github.com/ashcoft/pol/commit/9e451d12e81589e54ae42d401925606b007c8540))

* mlm log ([`ec0f9c5`](https://github.com/ashcoft/pol/commit/ec0f9c5ea483a9ac6c381d1406fbd332dfc80916))

* log format ([`c5811b8`](https://github.com/ashcoft/pol/commit/c5811b82136d17ea941a2715bc92955e2544ddab))

* memory leak monitor ([`ff8ecdd`](https://github.com/ashcoft/pol/commit/ff8ecdd4eb77b9917f07d6d3619753798458b97c))

* mem mon fix ([`6ab6e55`](https://github.com/ashcoft/pol/commit/6ab6e553b1fb3f9a8c05ec1ca87b73f6186ce1df))

* found mem leak ([`15878f8`](https://github.com/ashcoft/pol/commit/15878f8ad4500792b5c1de6217985c3cf5334130))

* mem leak in progress ([`3f1fec7`](https://github.com/ashcoft/pol/commit/3f1fec7cfa7c54afc29c61d0a477ed2eb48578b0))

* mem profiler (2) ([`8251793`](https://github.com/ashcoft/pol/commit/82517931a8de887bf870eb67bd332362e047ea48))

* mem profiler (1) ([`05572b5`](https://github.com/ashcoft/pol/commit/05572b5ea46b4a3606e67fe0a6fe6375865463ea))

* mem profiler ([`156d492`](https://github.com/ashcoft/pol/commit/156d492e1c90af7c445e2098eac6fc9fdb879675))

* debug ([`d9c5b3c`](https://github.com/ashcoft/pol/commit/d9c5b3c0c9865927a2351355aed91a016d0e69a7))

* gc ([`acde8d3`](https://github.com/ashcoft/pol/commit/acde8d3d8dad5b3b0c306f293f02e595ff63ac6b))

* req-s ([`2bdfc6e`](https://github.com/ashcoft/pol/commit/2bdfc6e0a3b1d946bf23f928b262168be0c362bb))

* req-s ([`1851bae`](https://github.com/ashcoft/pol/commit/1851baeba1c32897642a7c4fdd5ca22c5e3ae88e))

* compression ([`f898beb`](https://github.com/ashcoft/pol/commit/f898beb47c6ef362dda912d74c71e8295151ba8e))

* preview link only ([`3cb81db`](https://github.com/ashcoft/pol/commit/3cb81dbcc734e747d5aa6a4c8914242ad7765230))

* posts html preview ([`7871752`](https://github.com/ashcoft/pol/commit/78717525401868c8ddf225f6a330ce1228f2a7eb))

* posts html preview ([`136b892`](https://github.com/ashcoft/pol/commit/136b89218172e5824746d764db5fb2b405ec97ab))

* xpath results ([`69c4732`](https://github.com/ashcoft/pol/commit/69c4732455044ae404b4d2a6e5323ae6906062cf))

* duplicate link ([`2935090`](https://github.com/ashcoft/pol/commit/2935090acdeb47bc77bc1496a8608c71561e0680))

* skip certificate verification ([`bb9dc3c`](https://github.com/ashcoft/pol/commit/bb9dc3cc55ba4a240ef0828aa797d594473e6da7))

* request uri in error log ([`ee82b45`](https://github.com/ashcoft/pol/commit/ee82b45a22d69cdd80cc258e600753e065c87051))

* translations fix ([`9325b17`](https://github.com/ashcoft/pol/commit/9325b17a09a0a16163f73b2927a7652cd7bd4206))

* xpath editor ([`5cda918`](https://github.com/ashcoft/pol/commit/5cda918fa4a799d57adeef469161ad410d581500))

* xpath editor ([`cefe9e7`](https://github.com/ashcoft/pol/commit/cefe9e79d42f1a8f902229b60b4861a73219dd9a))

* xpath editor in progress ([`afd10fd`](https://github.com/ashcoft/pol/commit/afd10fdf6de90196c0e6195c2630151761688a40))

* xpath editor in progress ([`84c6b96`](https://github.com/ashcoft/pol/commit/84c6b9683814c9575efbb03e7cf9051c03cd02e9))

* xpath in progress ([`e846b63`](https://github.com/ashcoft/pol/commit/e846b63c97616326c4bfe39325c499a0884cc449))

* xpath editor in progress ([`c64602b`](https://github.com/ashcoft/pol/commit/c64602b3a40be65a047e6bce020f2e505d09c204))

* xpathes in progress ([`0bde3df`](https://github.com/ashcoft/pol/commit/0bde3df8a9e5cff340effaa443e72af32e1f9646))

* translations (1) ([`a08a1b3`](https://github.com/ashcoft/pol/commit/a08a1b3675b41911856960bc80615538d7defa2d))

* translations ([`a60f5d2`](https://github.com/ashcoft/pol/commit/a60f5d27fb66b279a824278a4d39984dc262a498))

* xpath autosave ([`a040bec`](https://github.com/ashcoft/pol/commit/a040bec0048a7f2d1ef61d69aba033bcbb8d6e35))

* xpath editor inputs layout in progress ([`7eb74a8`](https://github.com/ashcoft/pol/commit/7eb74a8f7348af3028141b79b4f2db7c3258eab7))

* xpath editor ui ([`8e84096`](https://github.com/ashcoft/pol/commit/8e840961c7974b365381b8dade7d0d191c6cdbd4))

* xpath editor (2) ([`648332c`](https://github.com/ashcoft/pol/commit/648332c1d79faf038a22c0677492ef29573fac12))

* xpath editor (1) ([`6af7e6d`](https://github.com/ashcoft/pol/commit/6af7e6d351816f37556ef0ff4ef1b93252d2af12))

* xpath editor in progress ([`5f76c3b`](https://github.com/ashcoft/pol/commit/5f76c3b6514e055b0d6ce27da5fe76639caf12fc))

* remove not used code ([`ce87e7d`](https://github.com/ashcoft/pol/commit/ce87e7d00c15c5d29df10588084cb58eac7e4ae9))

* fix warning ([`4fefd44`](https://github.com/ashcoft/pol/commit/4fefd44cf2036677222e61851b943e3a5406795a))

* rss guid ([`8bad52d`](https://github.com/ashcoft/pol/commit/8bad52dd0a505e7702a21003e4f00922497efbf3))

* html2json hotfix ([`fbfb6c8`](https://github.com/ashcoft/pol/commit/fbfb6c8638caa158124efd7a0d78d84f01f83f5c))

* html2json hotfix ([`b0881ce`](https://github.com/ashcoft/pol/commit/b0881ce3755092c6cb4348e10b1fec92c699a1d5))

* scrapy 1.4 ([`1093117`](https://github.com/ashcoft/pol/commit/10931178d68e22b5465827123c613860216ff3dc))

* Merge branch &#39;encoding&#39; of github.com:taroved/pol into exception_200 ([`839d220`](https://github.com/ashcoft/pol/commit/839d220ae7916763f4022314d3db1c267bc9e1e0))

* html error ([`b15bb34`](https://github.com/ashcoft/pol/commit/b15bb346944bc50ec707d64fdb534999ee77f70a))

* invalid headers: no chanked or content-length ([`b314082`](https://github.com/ashcoft/pol/commit/b3140827b9e40a6fdd8b9cb68daf52cef1d75860))

* fix tests ([`615215f`](https://github.com/ashcoft/pol/commit/615215ff164fe3cd3b786707fd2b5fcc87855b78))

* remove try catch ([`27de6c7`](https://github.com/ashcoft/pol/commit/27de6c73631103e6bf8e304f39abd7e8738fc968))

* encoding fix ([`ed50a76`](https://github.com/ashcoft/pol/commit/ed50a76498a2337d2a931226b04dbc794bf6b5d7))

* contacts in error messages ([`68adadd`](https://github.com/ashcoft/pol/commit/68adadd3946e1c3c68c9d02811fa0f402c1c39ac))

* tmp fix + tests ([`f2f8239`](https://github.com/ashcoft/pol/commit/f2f823974dde1a3e52c3da21aeae6db8eb11a8d4))

* url in error log ([`2678033`](https://github.com/ashcoft/pol/commit/26780338a8c86aee93dccac6ba91550b203ace04))

* add link field ([`f1589f3`](https://github.com/ashcoft/pol/commit/f1589f3e5e5cec74d46537863cf942c11beba011))

* mysql connection to utf8 ([`64e66b9`](https://github.com/ashcoft/pol/commit/64e66b9f832b8d5855d7aa3e1cc7df4d90fa3a32))

* posts time saving ([`acc4b6f`](https://github.com/ashcoft/pol/commit/acc4b6fd8586e37355407e4987d6554164851bd8))

* feeder time distance fix in progress ([`c3b4a68`](https://github.com/ashcoft/pol/commit/c3b4a6835da5396f147c7d6e996c0e0de231a7f0))

* fix inner html + test ([`576da9c`](https://github.com/ashcoft/pol/commit/576da9ca7ab6efc0df0e70aa808a91d4ffc14535))

* elements tails for text ([`9ac0f13`](https://github.com/ashcoft/pol/commit/9ac0f135818a5e54ef7545a2ea216cc50c7dbd8c))

* video fix ([`ef235a9`](https://github.com/ashcoft/pol/commit/ef235a9d09b42aae90384e028118087d2233f4f2))

* help button (1) ([`55a26f9`](https://github.com/ashcoft/pol/commit/55a26f9ca2d780ef4a1dbff219b93d98fd6cdcbb))

* help button ([`85a2d25`](https://github.com/ashcoft/pol/commit/85a2d253df92ee8c4a529d39995155548d178163))

* contacts template ([`69a204b`](https://github.com/ashcoft/pol/commit/69a204ba24f4398a59a33f10054453aaecd83db8))

* contacts ([`ea8164f`](https://github.com/ashcoft/pol/commit/ea8164ff2c69dc30fe21412dc7511682cd991fec))

* twisted agent ([`5a15140`](https://github.com/ashcoft/pol/commit/5a151406823a7f90d1cf0729d27406ea2ddb71bf))

* st fix ([`3fe6d18`](https://github.com/ashcoft/pol/commit/3fe6d189a3c961139bc410db8cd8c32aa04ddcab))

* body in head fix ([`9f73deb`](https://github.com/ashcoft/pol/commit/9f73debac435e7773330b27c06bb9242d55fffb5))

* ns fix ([`1b172dc`](https://github.com/ashcoft/pol/commit/1b172dc72aaafcf147041e2c91895418129c4944))

* meta trans ([`c14df76`](https://github.com/ashcoft/pol/commit/c14df760b663940204f4aaa07a5fe764a3e78b6c))

* titles ([`1a4bd30`](https://github.com/ashcoft/pol/commit/1a4bd30d2a38189423d1372e216659f30e4a3555))

* st fix ([`6d7ff4a`](https://github.com/ashcoft/pol/commit/6d7ff4a828b21e542d944ab13519c9cd035e5358))

* st fix ([`6faa47d`](https://github.com/ashcoft/pol/commit/6faa47dec5790e894607165b0e126206f60a4b99))

* st fix ([`289bce6`](https://github.com/ashcoft/pol/commit/289bce621d1beb26eeeece9501804fa19cc08fd3))

* msg fix ([`bb30378`](https://github.com/ashcoft/pol/commit/bb30378378bfeb143e909780e50fb42a1b48bb1f))

* st fix ([`49d3f05`](https://github.com/ashcoft/pol/commit/49d3f05d12c2fa2105af2f816684624f966fb6ae))

* md5 hash suffix to rss links ([`51dcd46`](https://github.com/ashcoft/pol/commit/51dcd46df6a6e56aaa1d1efc6bc47f6b56e3a70b))

* readme ([`1c254e4`](https://github.com/ashcoft/pol/commit/1c254e4ca8e6f3d7abe4febc2f0cf2abca33ee73))

* translation fix ([`99f81e2`](https://github.com/ashcoft/pol/commit/99f81e29a55f35ffa1d756f3e3ed0da82222b887))

* timer fix ([`d70a8b1`](https://github.com/ashcoft/pol/commit/d70a8b126ce4612a0bc2820684309bf9e755512c))

* limit requsts with redis + debug mode ([`ae54af5`](https://github.com/ashcoft/pol/commit/ae54af5ff3e782575c39e9feb45badae79fc63ac))

* readme ([`1dda85f`](https://github.com/ashcoft/pol/commit/1dda85f25799029b5682abc901bbd69499961f5e))

* readme ([`9163d36`](https://github.com/ashcoft/pol/commit/9163d363a3bd4dd1384a7f53556d77975cbe7ce7))

* user agent + feed1 ([`06f5706`](https://github.com/ashcoft/pol/commit/06f57064ac7d38d35d8b18bb6c0c4d050b9ca546))

* LICENSE created ([`8a4eedb`](https://github.com/ashcoft/pol/commit/8a4eedb4ef91479f6514c4de4bd49deae88584b2))

* readme.md edited ([`cc3d6bf`](https://github.com/ashcoft/pol/commit/cc3d6bf3fdd766e91d93d13d98dd881b79e1c7ec))

* readme.md edited ([`8a70397`](https://github.com/ashcoft/pol/commit/8a70397902d668d811a67e17f669e744b0e03dc0))

* readme.md edited ([`2f0dd66`](https://github.com/ashcoft/pol/commit/2f0dd66912a0d6589500cd77f5941b312922b8c0))

* readme.md edited ([`4714e5f`](https://github.com/ashcoft/pol/commit/4714e5f7375eb9e2e3e752c5b658910ec0a97dd6))

* readme.md edited ([`467323b`](https://github.com/ashcoft/pol/commit/467323b6bec0f9eaaf697f0a7722db1a78b940bf))

* repo title with image ([`765b6f0`](https://github.com/ashcoft/pol/commit/765b6f076bb7e078ea0d27287240bbbb67b83c4a))

* copyright ([`569ca82`](https://github.com/ashcoft/pol/commit/569ca829d834de323d9c69af3a5a6ad0071a0aef))

* feed link title ([`e2b029d`](https://github.com/ashcoft/pol/commit/e2b029d536f270c346752b7e65a27b6eb802cce5))

* readme ([`3c1ca29`](https://github.com/ashcoft/pol/commit/3c1ca29252652c7e31d98a2e1d4ddaa3fd396772))

* readme ([`1d1f8f9`](https://github.com/ashcoft/pol/commit/1d1f8f905e7992f188a9a917b668b2f97538d011))

* readme ([`4e13a72`](https://github.com/ashcoft/pol/commit/4e13a722d8297e04fb6704ecf9dce473e5588042))

* title link fix ([`47156b6`](https://github.com/ashcoft/pol/commit/47156b6465cb26c35a034851f2c710dfbec30058))

* link detect in progress ([`3f2c9f6`](https://github.com/ashcoft/pol/commit/3f2c9f6624d69b2e6f51e215471171d405deea9e))

* new hover logic fix ([`964b3e7`](https://github.com/ashcoft/pol/commit/964b3e70d235e15d6b506458f6392042568f2a41))

* hover logic (test version) ([`3b440fd`](https://github.com/ashcoft/pol/commit/3b440fd70e70ef253c70c230a51938884bcb2fd8))

* spinner ([`2a81c5d`](https://github.com/ashcoft/pol/commit/2a81c5d5c944581efc34b8153184cfa69676bd5f))

* translations ([`f63531f`](https://github.com/ashcoft/pol/commit/f63531fdd153c36a05f67658527736c0b061fab8))

* settings fix ([`203e6e6`](https://github.com/ashcoft/pol/commit/203e6e69d83b70b71d8a5a87992388303836ee7c))

* rss link + nginx config ([`8f2b91e`](https://github.com/ashcoft/pol/commit/8f2b91e2793e9165cd216c6a5cac06f435e493b4))

* requirements.txt updated ([`f97fc9f`](https://github.com/ashcoft/pol/commit/f97fc9fd84c53d3dd54e1ce54e547aa11c75914e))

* fixed feed generator problem + several immprovements ([`a53952b`](https://github.com/ashcoft/pol/commit/a53952b9f05c2dedfa67c467640794fe2708e844))

* feed generator is working ([`ce8432f`](https://github.com/ashcoft/pol/commit/ce8432fb55956c7df4dfde2c07872a459105f0a8))

* create feed is ready ([`54e6dd0`](https://github.com/ashcoft/pol/commit/54e6dd0462cc0f850e4ab4e68157bc368df90b64))

* fixed setup tool js ([`f29c146`](https://github.com/ashcoft/pol/commit/f29c14699e56dc8a7729fb743407844445c0bd38))

* &#39;Create&#39; button + db models ([`e1c5b38`](https://github.com/ashcoft/pol/commit/e1c5b3849b7c0bab095e30e94ab640aa7c5e4076))

* setup tools working well; hover highlight is not finished ([`20114d0`](https://github.com/ashcoft/pol/commit/20114d0f42bab91260ea7c10d5dd19e249384892))

* rewrited setup tool js ([`ace68c6`](https://github.com/ashcoft/pol/commit/ace68c697929fbb6a24c392a1b508af2b387fb70))

* setup tool refactoring is in progress ([`aeae7e3`](https://github.com/ashcoft/pol/commit/aeae7e3dc7cd661827a30e8f130e2d01f300295e))

* update requirenemts ([`41a319b`](https://github.com/ashcoft/pol/commit/41a319b7a23f615d0a46b60496be46ff4e926cd8))

* update settings ([`1a75062`](https://github.com/ashcoft/pol/commit/1a75062a68aa86b1dc9ed7b1686dc292de123e43))

* setup-tool in progress; +requirements.txt ([`d5b23f0`](https://github.com/ashcoft/pol/commit/d5b23f0e1039d50a92c6e00241ae68270fb3b448))

* server calculation is fixed; client elements selection is in progress ([`cc94859`](https://github.com/ashcoft/pol/commit/cc9485983c7de6ca4e2e0012992ce86f9b8c7185))

* first version of selection calculation is ready ([`24816ed`](https://github.com/ashcoft/pol/commit/24816edb3365392194a1b22d9dcb76d09d653e15))

* server tag-id selection is in progress ([`c7af38f`](https://github.com/ashcoft/pol/commit/c7af38f8e3e8c2c465fc7b14db035e3d7d5efcd5))

* description button; sending of html and getting of response ([`2059b0a`](https://github.com/ashcoft/pol/commit/2059b0a520f99df1621d4cf892b5b45d80b0d0ce))

* setup tool: slightly different yellow background ([`1bbf63c`](https://github.com/ashcoft/pol/commit/1bbf63c5cbb0a681e7aeab7afa6005194200a712))

* setup tool: title button is ready ([`8e5a8d9`](https://github.com/ashcoft/pol/commit/8e5a8d9886c863b0428f6d6c313e4e39d80e8287))

* html generation fixed; setup tool buttons in progress ([`f6cb283`](https://github.com/ashcoft/pol/commit/f6cb283599f543b20430324f6ce40571ee8db18e))

* picking in progress ([`665cdc5`](https://github.com/ashcoft/pol/commit/665cdc5d76eb9bc14eb2004a3cce32f394d8d5e4))

* fix scrapy response ([`853cf4d`](https://github.com/ashcoft/pol/commit/853cf4db17e8b9c5fbe7455bc3edcbd1a11f981e))

* setup page started ([`e872513`](https://github.com/ashcoft/pol/commit/e872513c33758d2b1009780d8d796a4131a198d7))

* django project ([`415e1f3`](https://github.com/ashcoft/pol/commit/415e1f3c94e04b66e53b339137789baff796b829))

* getting of html with base and with no scripts ([`30e80f7`](https://github.com/ashcoft/pol/commit/30e80f7bff8a73ead32e3c6ef7e6a40fd2fcdcac))

* parse url as json parameter ([`87bbd2a`](https://github.com/ashcoft/pol/commit/87bbd2a4b16433b8b2fbe01ac39b18e43dae70ab))
