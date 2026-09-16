import sys
from pathlib import Path

# The package every composite action runs. On a runner each reaches it from its own action path's parent;
# here the directory holding it goes on `sys.path` directly. pyright reaches it through `extraPaths`.
sys.path.insert(0, str(Path(__file__).parent.parent / "actions"))
