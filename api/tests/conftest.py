import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient 

from api.main import app
from api.db.db import init_db

@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_ledger.sqlite"
    os.environ["DB_PATH"] = str(db_file)

    init_db()

    with TestClient(app) as test_client:
        yield test_client