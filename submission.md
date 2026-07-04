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
- **Navigation Strategy**: Traced the streak update path from `routes/songs.py:listen` -> `streak_service.py:record_listening_event` -> `streak_service.py:update_listening_streak`.
- **Root Cause**: The condition `elif days_since_last == 1 and today.weekday() != 6` explicitly prevented streaks from incrementing on Sundays. Since Python's `datetime.weekday()` returns 6 for Sunday, the condition failed every Sunday, falling through to the `else` block which resets the streak to 1.
- **Fix**: Removed the `and today.weekday() != 6` clause from the increment logic in `update_listening_streak`, ensuring all consecutive calendar days are treated equally as per the Docstring Contract.
- **Side-Effect Check**: Verified that the streak still correctly resets to 1 if a day is skipped (e.g., Friday to Sunday) and remains unchanged if multiple listens occur on the same day. Added regression tests in `tests/test_streaks.py` covering these cases.

### Issue #2: Friends Listening Now shows people from yesterday
- **Reproduction**: Created a listening event for a friend 12 hours ago.
- **Navigation Strategy**: Traced `GET /feed/<id>/listening-now` to `feed_service.py:get_friends_listening_now`. Observed the `RECENT_THRESHOLD` constant.
- **Root Cause**: The `RECENT_THRESHOLD` was previously set to `timedelta(hours=24)`. This meant the feed showed anyone who listened in the last day, which contradicts the "Listening Now" (10-minute threshold) requirement.
- **Fix and Side-Effect Check**: Updated `RECENT_THRESHOLD` to 10 minutes. Verified with `tests/test_feed_threshold.py`. Side-effect check: Confirmed that `get_activity_feed` is unaffected as it doesn't use the threshold.

### Issue #3: The same song keeps showing up twice in search
- **Reproduction**: Searched for a song with multiple tags. The raw SQL result set contained duplicate entries for the song.
- **Navigation Strategy**: Traced `GET /songs/search` to `search_service.py:search_songs`. Inspected the SQLAlchemy query construction.
- **Root Cause**: The query performed an `outerjoin(song_tags)` but only filtered on `Song` fields. Because a join with the association table returns one row per tag for a song, songs with multiple tags were duplicated in the raw SQL result set.
- **Fix and Side-Effect Check**: Removed the redundant `outerjoin`. Since tags are already loaded via a `lazy="subquery"` relationship on the `Song` model, the join was unnecessary for the current search criteria (title and artist). Verified with `tests/test_search_duplicates.py` and `tests/test_search.py`.

### Issue #4: Missing notification for song ratings
- **Reproduction**: Rated a song shared by a friend and checked that friend's notifications.
- **Navigation Strategy**: Compared `notification_service.py:add_to_playlist` (which sends notifications) with `rate_song`.
- **Root Cause**: The `rate_song` function implemented the rating logic but lacked the call to `create_notification`.
- **Fix and Side-Effect Check**: Added a call to `create_notification` inside `rate_song`, targeted at `song.shared_by`. Verified with `tests/test_notifications.py`. Side-effect check: Confirmed that users do not receive notifications for rating their own songs.

### Issue #5: The last song in a playlist never shows up
- **Reproduction**: Created a playlist with 3 songs and fetched its contents. Only 2 songs were returned.
- **Navigation Strategy**: Traced `GET /playlists/<id>/songs` to `playlist_service.py:get_playlist_songs`. Inspected the return statement.
- **Root Cause**: The function was returning `songs[:-1]`. This Python slice excludes the last element of the list, violating the Docstring Contract which promises "all songs in the playlist."
- **Fix and Side-Effect Check**: Ensure the full list is returned without slicing. Verified with `tests/test_playlist_songs.py`. Side-effect check: Confirmed that ordering is preserved by the SQL query.
