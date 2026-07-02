import pytest
from datetime import datetime, timedelta, timezone
from app import create_app, db
from models import User, Song, ListeningEvent
from services.feed_service import get_friends_listening_now

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def users(app):
    with app.app_context():
        u1 = User(username="user1", email="u1@example.com")
        u2 = User(username="user2", email="u2@example.com")
        u3 = User(username="user3", email="u3@example.com")
        db.session.add_all([u1, u2, u3])
        u1.friends.append(u2)
        u1.friends.append(u3)
        db.session.commit()
        return [u1.id, u2.id, u3.id]

@pytest.fixture
def song(app, users):
    with app.app_context():
        s = Song(title="Test Song", artist="Test Artist", shared_by=users[0])
        db.session.add(s)
        db.session.commit()
        return s.id

def test_friends_listening_now_threshold(app, users, song):
    u1_id, u2_id, u3_id = users
    with app.app_context():
        now = datetime.now(timezone.utc)
        event1 = ListeningEvent(user_id=u2_id, song_id=song, listened_at=now - timedelta(minutes=5))
        event2 = ListeningEvent(user_id=u3_id, song_id=song, listened_at=now - timedelta(minutes=15))
        db.session.add_all([event1, event2])
        db.session.commit()
        feed = get_friends_listening_now(u1_id)
        assert len(feed) == 1
        assert feed[0]["friend"]["id"] == u2_id
