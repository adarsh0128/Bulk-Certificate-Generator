import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("STORAGE_DIR", str(Path(__file__).parent / "tmp_storage"))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import config as config_module
from app.db import session as session_module
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client_and_db(tmp_path):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    config_module.settings.DATABASE_URL = "sqlite://"
    config_module.settings.STORAGE_DIR = str(storage_dir)

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session_module.engine = engine
    session_module.SessionLocal = SessionLocal

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, SessionLocal
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
