import pytest
import requests
from playwright.sync_api import Page, expect
from datetime import datetime, timedelta, timezone
import subprocess
import time
import os
import sqlite3

# Base URL for the local server
BASE_URL = "http://127.0.0.1:5000"

def get_nova_id():
    conn = sqlite3.connect("instance/mixtape.db")
    c = conn.cursor()
    c.execute("SELECT id FROM user WHERE username='nova'")
    res = c.fetchone()
    conn.close()
    return res[0] if res else None

@pytest.fixture(scope="module", autouse=True)
def server():
    # Start the server
    env = os.environ.copy()
    env["FLASK_APP"] = "app:create_app"
    subprocess.run(["python", "seed_data.py"], check=True)

    proc = subprocess.Popen(["flask", "run"], env=env)
    time.sleep(3)  # Wait for server to start
    yield
    proc.terminate()

def test_streak_reset_fix(page: Page):
    user_id = get_nova_id()
    page.goto(f"{BASE_URL}/users/{user_id}/streak")
    # Response should be JSON like {"streak": 7, "user_id": "..."}
    # We'll use page.content() or locator for text content
    expect(page.locator("body")).to_contain_text('"streak":')

def test_feed_threshold_fix(page: Page):
    user_id = get_nova_id()
    page.goto(f"{BASE_URL}/feed/{user_id}/listening-now")
    expect(page.locator("body")).to_contain_text('"feed":')

def test_search_duplicates_fix(page: Page):
    page.goto(f"{BASE_URL}/songs/search?q=Harlem")
    expect(page.locator("body")).to_contain_text('"count":1')

def test_notification_missing_fix(page: Page):
    nova_id = get_nova_id()
    # Get a song ID
    resp = requests.get(f"{BASE_URL}/songs/search?q=Harlem").json()
    song_id = resp['results'][0]['id']
    sharer_id = resp['results'][0]['shared_by']

    users = requests.get(f"{BASE_URL}/feed/{sharer_id}/activity").json()['feed']
    rater_id = users[0]['friend']['id']

    requests.post(f"{BASE_URL}/songs/{song_id}/rate", json={"user_id": rater_id, "score": 5})

    page.goto(f"{BASE_URL}/users/{sharer_id}/notifications")
    expect(page.locator("body")).to_contain_text("rated your song")

def test_playlist_position_fix(page: Page):
    conn = sqlite3.connect("instance/mixtape.db")
    c = conn.cursor()
    c.execute("SELECT playlist_id, count(*) FROM playlist_entries GROUP BY playlist_id LIMIT 1")
    pid, expected_count = c.fetchone()
    conn.close()

    page.goto(f"{BASE_URL}/playlists/{pid}/songs")
    expect(page.locator("body")).to_contain_text(f'"count":{expected_count}')
