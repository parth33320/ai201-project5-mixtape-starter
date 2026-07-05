# Mixtape Bug Hunt - Submission

## Codebase Map

The Mixtape application is structured as follows:

- **app.py**: The application factory. Initializes Flask, SQLAlchemy, and sets up the database.
- **models.py**: Contains all SQLAlchemy models (`User`, `Song`, `Playlist`, `ListeningEvent`, `Rating`, `Notification`). Defines relationships such as friendships and playlist entries.
- **routes/**:
  - `feed.py`: Endpoints for the activity feed and "Friends Listening Now".
  - `playlists.py`: Management of playlists and their contents.
  - `songs.py`: Song discovery, sharing, and rating.
  - `users.py`: User profiles, streaks, and notifications.
- **services/**:
  - `streak_service.py`: Logic for maintaining user listening streaks.
  - `feed_service.py`: Filters and aggregates activity for feeds based on the `Friends Feed Threshold`.
  - `search_service.py`: Song search logic using title and artist.
  - `notification_service.py`: Generation and retrieval of social notifications.
  - `playlist_service.py`: Ordering and retrieval of playlist songs.

**Data Flow Example: Song Rating Notification**
1.  **Route**: A `POST` request to `/songs/<id>/rate` is received by `routes/songs.py:rate()`.
2.  **Service**: It calls `notification_service.rate_song()`.
3.  **Logic**: The service updates the `Rating` in the database and calls `create_notification()` to alert the song sharer.
4.  **Model**: A new `Notification` record is created in the database, targeted at the song sharer identified by `song.shared_by`.
5.  **Return**: The updated rating is returned to the route, which sends a JSON response to the client.

---

## Root Cause Analysis

### Issue #1: My listening streak keeps resetting
- **Reproduction**: Manually set a user's `last_listened_at` to a Saturday (e.g., 2024-06-15) and `listening_streak` to 1. Submit a listening event for the following Sunday (2024-06-16).
- **Navigation Strategy**: Traced the streak update path from `routes/songs.py:listen` -> `streak_service.py:record_listening_event` -> `streak_service.py:update_listening_streak`. This root cause is identified by running `today.weekday()` in a Python shell; seeing it return 6 for Sunday proved that the != 6 check in the code was explicitly resetting streaks on the very day users are most likely to listen.
- **Root Cause**: The condition `elif days_since_last == 1 and today.weekday() != 6` explicitly prevented streaks from incrementing on Sundays. Since Python's `datetime.weekday()` returns 6 for Sunday, the condition failed every Sunday, falling through to the `else` block which resets the streak to 1.
- **Fix**: Removed the `and today.weekday() != 6` clause from the increment logic in `update_listening_streak`, ensuring all consecutive calendar days are treated equally as per the Docstring Contract.
- **Side-Effect Check**: Verified that the streak still correctly resets to 1 if a day is skipped (e.g., Friday to Sunday) and remains unchanged if multiple listens occur on the same day. Added regression tests in `tests/test_streaks.py` covering these cases.

### Issue #2: Friends Listening Now shows people from yesterday
- **Reproduction**: Created a listening event for a friend 12 hours ago.
- **Navigation Strategy**: Traced `GET /feed/<id>/listening-now` to `feed_service.py:get_friends_listening_now`. Observed the `RECENT_THRESHOLD` constant. I found the root cause upon inspecting the RECENT_THRESHOLD constant; seeing it set to 24 hours made it clear why the "Listening Now" feed was erroneously populated with activity from the previous day.
- **Root Cause**: The `RECENT_THRESHOLD` was previously set to `timedelta(hours=24)`. This meant the feed showed anyone who listened in the last day, which contradicts the "Listening Now" (10-minute threshold) requirement.
- **Fix**: Updated `RECENT_THRESHOLD` to 10 minutes. Verified with `tests/test_feed_threshold.py`.
- **Side-effect check**: Confirmed that `get_activity_feed` is unaffected as it doesn't use the threshold.

### Issue #3: The same song keeps showing up twice in search
- **Reproduction**: Searched for a song with multiple tags. The raw SQL result set contained duplicate entries for the song.
- **Navigation Strategy**: Traced `GET /songs/search` to `search_service.py:search_songs`. Inspected the SQLAlchemy query construction. I identified the `outerjoin(song_tags)` in the query; I realized that because the database returns one row for every tag associated with a song, this join was causing row multiplication in the result set for songs with multiple tags
- **Root Cause**: The query performed an `outerjoin(song_tags)` but only filtered on `Song` fields. Because a join with the association table returns one row per tag for a song, songs with multiple tags were duplicated in the raw SQL result set.
- **Fix**: Removed the redundant `outerjoin` from the query in `search_service.py`.
- **Side-Effect Check**: Verified that tags still load correctly via the `lazy="subquery"` relationship. Confirmed that search still works by title and artist, and results are unique even for songs with multiple tags. Verified with `tests/test_search_duplicates.py` and `tests/test_search.py`.

### Issue #4: Missing notification for song ratings
- **Reproduction**: Rated a song shared by a friend and checked that friend's notifications.
- **Navigation Strategy**: Compared `notification_service.py:add_to_playlist` (which sends notifications) with `rate_song`. I saw that `rate_song` lacked any call to `create_notification()`, leaving the Docstring Contract for social alerts unfulfilled despite the rating being saved to the database.
- **Root Cause**: The `rate_song` function implemented the rating logic but lacked the call to `create_notification`.
- **Fix**: Added a call to `create_notification` inside `rate_song`, targeted at `song.shared_by`. Verified with `tests/test_notifications.py`.
- **Side-effect check**: Confirmed that users do not receive notifications for rating their own songs. Confirmed users don't get notifications for self-rating. This check is sufficient because it ensures the new trigger respects the Docstring Contract to only notify the sharer.

### Issue #5: The last song in a playlist never shows up
- **Reproduction**: Created a playlist with 3 songs and fetched its contents. Only 2 songs were returned.
- **Navigation Strategy**: Traced `GET /playlists/<id>/songs` to `playlist_service.py:get_playlist_songs`. I saw the `songs[:-1]` slice in the return statement; I recognized this as the specific logic discarding the final element of the list before it reached the client.
- **Root Cause**: The function was returning `songs[:-1]`. This Python slice excludes the last element of the list, violating the Docstring Contract which promises "all songs in the playlist."
- **Fix**: Ensure the full list is returned without slicing. Verified with `tests/test_playlist_songs.py`.
- **Side-effect check**: Confirmed that ordering is preserved by the SQL query. Confirmed ordering is preserved. This is sufficient because it proves removing the Python slice did not interfere with the `ORDER BY position` logic in the SQLAlchemy query.

## AI Usage
- **Use 1 (Date Logic)**: I asked the AI to explain the return values of Python's `datetime.weekday()` versus `isoweekday()`. This helped me identify that the code's check for `!= 6` was explicitly blocking Sunday increments, which directly contradicted our Docstring Contract. 
- **Use 2 (SQL Tracing)**: I used the AI to summarize the `search_service.py` module and explain how SQLAlchemy handles many-to-many relationships. It helped me trace how the Song model connects to Tag via the `song_tags` association table.
- **Course-Correction**: During the search duplicate hunt (Issue #3), the AI initially suggested adding a `.distinct()` call to the query. However, I verified the SQLAlchemy query construction and realized the root cause was a redundant `outerjoin(song_tags)`. I overrode the AI's suggestion and performed a deeper fix by removing the unnecessary join, as the tags were already configured for lazy="subquery" loading in `models.py`.

## Regression Test Evidence
- **Test File**: `tests/test_playlist_songs_fix.py`
- **Behavior Verified**: Verifies that every song assigned to a playlist is returned in the response.
- **Failure Analysis**: This test would have failed against the buggy code because the `get_playlist_songs` function used a Python `slice [:-1]`. While the test expects a list length of 3, the buggy implementation would have returned only 2 songs, triggering an `AssertionError`.
