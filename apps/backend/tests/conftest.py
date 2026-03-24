import os
from pathlib import Path
import sys
from uuid import uuid4

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(autouse=True)
def isolated_sqlite(tmp_path: Path):
    database_path = tmp_path / f"test-{uuid4().hex}.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)

    yield

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name, None)
