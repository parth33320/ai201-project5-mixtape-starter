import pytest
from app import create_app, db
from models import User, Song, Playlist, playlist_entries
from services.playlist_service import get_playlist_songs

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def playlist_with_songs(app):
    with app.app_context():
        u = User(username="creator", email="c@example.com")
        db.session.add(u)
        db.session.flush()
        p = Playlist(name="Test Playlist", created_by=u.id)
        db.session.add(p)
        db.session.flush()
        s1 = Song(title="Song 1", artist="Artist", shared_by=u.id)
        s2 = Song(title="Song 2", artist="Artist", shared_by=u.id)
        s3 = Song(title="Song 3", artist="Artist", shared_by=u.id)
        db.session.add_all([s1, s2, s3])
        db.session.flush()
        db.session.execute(playlist_entries.insert().values(playlist_id=p.id, song_id=s1.id, position=1, added_by=u.id))
        db.session.execute(playlist_entries.insert().values(playlist_id=p.id, song_id=s2.id, position=2, added_by=u.id))
        db.session.execute(playlist_entries.insert().values(playlist_id=p.id, song_id=s3.id, position=3, added_by=u.id))
        db.session.commit()
        return p.id

def test_get_playlist_songs_returns_all_songs(app, playlist_with_songs):
    with app.app_context():
        songs = get_playlist_songs(playlist_with_songs)
        assert len(songs) == 3
