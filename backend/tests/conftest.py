import os
os.environ.setdefault('DATABASE_URL','sqlite:////tmp/shift-chroma-test.db')
os.environ.setdefault('REDIS_URL','redis://localhost:6379/0')
os.environ.setdefault('JWT_SECRET','test-secret')
import fakeredis
import redis as redis_lib
_FAKE=fakeredis.FakeStrictRedis()
redis_lib.Redis.from_url=lambda *a,**k:_FAKE
import pytest
from src.config.database import Base,engine,Session
from src.models import user,study,observation,candidate,quota,run,review,audit
from src.models.user import User
from src.utils.security import hash_password

@pytest.fixture()
def db():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
    with Session() as s:
        yield s

@pytest.fixture()
def users(db):
    from src.models.user import User
    for role in ('admin','analyst','viewer'):
        db.add(User(email=role+'@demo.local',role=role,password_hash=hash_password('Research2026!')))
    db.commit()
    return True

@pytest.fixture()
def client(db,users):
    from fastapi.testclient import TestClient
    from src.main import app
    return TestClient(app,raise_server_exceptions=False)

def login(client,email):
    r=client.post('/auth/login',json={'email':email,'password':'Research2026!'})
    assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['token']}
