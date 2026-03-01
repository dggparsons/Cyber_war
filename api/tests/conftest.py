"""Shared test fixtures."""
import pytest
from app import create_app
from app.extensions import db as _db, limiter


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "SERVER_NAME": "localhost",
    })
    # Disable rate limiting in tests
    limiter.enabled = False
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(autouse=True)
def _clean_db(app):
    """Roll back after each test to ensure isolation."""
    with app.app_context():
        yield
        _db.session.rollback()
        # Truncate all tables for clean state between tests
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    with app.app_context():
        yield _db
