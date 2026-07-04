import pytest
from app import create_app, db
from models import User, Song, Tag, song_tags
from services.search_service import search_songs
import inspect

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def song_with_tags(app):
    with app.app_context():
        u = User(username="sharer", email="sharer@example.com")
        db.session.add(u)
        db.session.flush()
        s = Song(title="Multi-Tag Song", artist="Artist", shared_by=u.id)
        t1 = Tag(name="tag1")
        t2 = Tag(name="tag2")
        db.session.add_all([s, t1, t2])
        db.session.flush()
        db.session.execute(song_tags.insert().values(song_id=s.id, tag_id=t1.id))
        db.session.execute(song_tags.insert().values(song_id=s.id, tag_id=t2.id))
        db.session.commit()
        return s.id

def test_search_no_duplicates(app, song_with_tags):
    """
    Ensure that searching for a song with multiple tags returns exactly one result.
    """
    with app.app_context():
        results = search_songs("Multi-Tag")
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"

def test_search_songs_does_not_contain_redundant_join():
    """
    Ensure that the search_songs implementation does not contain the redundant join
    that was causing duplicate rows at the database level.
    """
    source = inspect.getsource(search_songs)
    assert "outerjoin" not in source, "Found redundant 'outerjoin' in search_songs service."
