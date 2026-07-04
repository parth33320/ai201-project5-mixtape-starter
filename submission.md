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

---

## Root Cause Analysis

### Issue #1: My listening streak keeps resetting
- **Reproduction**: Set a user's `last_listened_at` to a Saturday. Submit a listening event for the following Sunday.
- **Navigation Strategy**: Traced `GET /users/<id>/streak` to `streak_service.py:get_streak`. Followed the update path in `record_listening_event` to `update_listening_streak`.
- **Root Cause**: The logic `elif days_since_last == 1 and today.weekday() != 6` contained a hardcoded "Sunday exception". In Python's `weekday()`, 6 is Sunday. This caused the streak to reset (falling into the `else: streak = 1` block) every Sunday, even if the user listened on Saturday.
- **Fix and Side-Effect Check**: Ensure the code treats all consecutive days equally by using `elif days_since_last == 1:`. Verified that skipping a day still correctly resets the streak by running `tests/test_streaks.py`.

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
