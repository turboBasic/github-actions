import sys
from pathlib import Path

# The package both composite actions run. On a runner each reaches it from its own action path's parent;
# here the directory holding it goes on the path directly. pyright reaches it through `extraPaths` in
# pyproject.toml.
sys.path.insert(0, str(Path(__file__).parent.parent / "actions"))
