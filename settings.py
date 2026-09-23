"""Repo-root settings facade.

The real Django settings module is generated at
"frontend/frontend/settings.py" from "settings.py.example" (git-ignored).
The downloader core imports settings from the repo root, so re-export it here.

This used to be a symlink to that generated file. Because the target is
git-ignored, the symlink was dangling on a fresh checkout, and anything that
resolves or archives every path in the tree then failed on it (notably the
GitHub Pages build).
"""

from frontend.frontend.settings import *  # noqa: F401,F403
