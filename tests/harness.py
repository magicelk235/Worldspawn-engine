"""Assemble a throwaway root for the checks.

The engine loads packages from ./packages relative to the working directory,
so anything committed there would load in a real game too. The example package
the checks run against lives in tests/fixtures instead, and each check gets a
temporary root holding the engine's data/ and a copy of that fixture.

A copy rather than a link, because some checks write into the package's assets.
"""

import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(REPO, "tests", "fixtures")


def buildRoot(packages=("package",)):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    root = tempfile.mkdtemp(prefix="worldspawn-check-")
    os.symlink(os.path.join(REPO, "data"), os.path.join(root, "data"))
    os.makedirs(os.path.join(root, "packages"))
    for name in packages:
        shutil.copytree(os.path.join(FIXTURES, name),
                        os.path.join(root, "packages", name))
    sys.path.insert(0, root)
    os.chdir(root)
    return root
