import pytest
from app import create_app, db
from models import User, Song, Notification
from services.notification_service import rate_song, get_notifications

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
        u1 = User(username="sharer", email="sharer@example.com")
        u2 = User(username="rater", email="rater@example.com")
        db.session.add_all([u1, u2])
        db.session.commit()
        return [u1.id, u2.id]

@pytest.fixture
def song(app, users):
    u1_id, u2_id = users
    with app.app_context():
        s = Song(title="Test Song", artist="Artist", shared_by=u1_id)
        db.session.add(s)
        db.session.commit()
        return s.id

def test_rating_creates_notification(app, users, song):
    u1_id, u2_id = users
    with app.app_context():
        rate_song(u2_id, song, 5)
        notifications = get_notifications(u1_id)
        assert len(notifications) == 1
        assert notifications[0]['type'] == 'song_rated'

def test_rating_own_song_does_not_create_notification(app, users, song):
    u1_id, u2_id = users
    with app.app_context():
        # u1 shared the song, u1 rates it
        rate_song(u1_id, song, 5)
        notifications = get_notifications(u1_id)
        assert len(notifications) == 0
