from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker

from app import models
from app.main import app
from app.database import Base
from app.routers.books import get_db

# Używamy bazy w pamienci RAM żeby nie twożyć zbędnuch plików
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_admin_required():
    return models.User(
        id=1,
        username="admin",
        is_admin=True
    )


#Podmieniamy baze dannych
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def setup_module(module):
    Base.metadata.create_all(bind=engine)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200

#Dodajemy książkę
def test_create_and_read_book():
    response = client.post(
        "/add-book",
        data={"title": "Test", "author": "Ttttt", "year": 2024},
        follow_redirects=False
    )
    assert response.status_code == 303
