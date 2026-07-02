# Mixtape Bug Hunt - Submission

## AI Usage Section

During this project, I collaborated with AI in several key areas to navigate the codebase and diagnose bugs:

1.  **Codebase Orientation**: I used AI to summarize the responsibilities of each file in the `services/` layer. Specifically, I asked for a trace of the listening streak logic to understand how `update_listening_streak` interacted with the `User` model. This helped me quickly identify the date-based logic as the primary area of interest for Issue #1.
2.  **Date Logic Clarification**: For the Streak Bug, I asked the AI to clarify the difference between Python's `datetime.weekday()` and `datetime.isoweekday()`. The AI explained that `weekday()` is 0-indexed starting Monday (0-6), which immediately highlighted why the existing `today.weekday() != 6` was causing a reset on Sundays.
3.  **Course-Correction (Search Duplicates)**: Initially, when investigating the search duplicate issue, the AI suggested that adding `.distinct()` to the SQLAlchemy query was the standard fix. However, upon manual inspection of the `Song` model, I noticed that tags were already being loaded via a `subquery` relationship. I realized that the `outerjoin(song_tags)` in `search_songs` was not just causing duplicates but was entirely redundant for the current search criteria (title and artist). I corrected the course by removing the redundant join altogether, which simplified the code and solved the root cause more elegantly than just masking it with `distinct()`.

## Codebase Map

The Mixtape application is organized into a clean layered architecture:

-   **app.py**: The factory for creating the Flask application and initializing the SQLAlchemy database.
-   **models.py**: Defines the data schema using SQLAlchemy. Key entities include `User`, `Song`, `Playlist`, and `ListeningEvent`. Relationships are well-defined, notably the many-to-many `playlist_entries` which includes a `position` column for ordering.
-   **routes/**: Entry points for HTTP requests. They handle request parsing and response formatting, delegating all business logic to the service layer.
-   **services/**: The "Logic Jungle" where the Docstring Contracts are implemented.
    -   `streak_service.py`: Manages consecutive listening streaks.
    -   `feed_service.py`: Calculates the "Friends Listening Now" and activity feeds.
    -   `search_service.py`: Handles song discovery.
    -   `notification_service.py`: Manages social alerts for song interactions.
    -   `playlist_service.py`: Handles playlist composition and ordering.

**Data Flow Example: Song Rating Notification**
1.  **Route**: A `POST` request to `/songs/<id>/rate` is received by `routes/songs.py:rate()`.
2.  **Service**: It calls `notification_service.rate_song()`.
3.  **Logic**: The service updates the `Rating` in the database. After fixing Bug #4, it now also calls `create_notification()`.
4.  **Model**: A new `Notification` record is created in the database, targeted at the user who originally shared the song (`song.shared_by`).
5.  **Return**: The updated rating is returned to the route, which sends a JSON response to the client.

---

## Root Cause Analysis

### Issue #1: My listening streak keeps resetting
-   **Reproduction**: Set a user's `last_listened_at` to a Saturday. Submit a listening event for the following Sunday.
-   **Navigation Strategy**: Traced `GET /users/<id>/streak` to `streak_service.py:get_streak`. Followed the update path in `record_listening_event` to `update_listening_streak`. Confirmed the logic by reading the source in `streak_service.py`.
-   **Root Cause**: The logic `elif days_since_last == 1 and today.weekday() != 6` contained a hardcoded "Sunday exception". In Python's `weekday()`, 6 is Sunday. This caused the streak to reset (falling into the `else: streak = 1` block) every Sunday, even if the user listened on Saturday.
-   **Fix and Side-Effect Check**: Removed the `and today.weekday() != 6` condition to treat all consecutive days equally. Side-effect check: Verified that skipping a day still correctly resets the streak by running `test_streak_resets_after_skipped_day`.

### Issue #2: Friends Listening Now shows people from yesterday
-   **Reproduction**: Created a listening event for a friend 12 hours ago. Noticed they still appeared in the "Listening Now" feed.
-   **Navigation Strategy**: Traced `GET /feed/<id>/listening-now` to `feed_service.py:get_friends_listening_now`. Observed the `RECENT_THRESHOLD` constant at the top of the file.
-   **Root Cause**: The `RECENT_THRESHOLD` was set to `timedelta(hours=24)`. This meant the feed was effectively showing "Friends who listened in the last day," which contradicts the "Listening Now" (10-minute threshold) requirement defined in the Ubiquitous Language.
-   **Fix and Side-Effect Check**: Updated `RECENT_THRESHOLD` to 10 minutes. Side-effect check: Verified that `get_activity_feed` still correctly shows historical events as it does not use the `RECENT_THRESHOLD`.

### Issue #3: The same song keeps showing up twice in search
-   **Reproduction**: Searched for "Harlem" (a song in seed data with 3 tags). The result appeared 3 times in the list.
-   **Navigation Strategy**: Traced `GET /songs/search` to `search_service.py:search_songs`. Inspected the SQLAlchemy query construction.
-   **Root Cause**: The query performed an `outerjoin(song_tags)` but only filtered on `Song` fields. Because a join with the association table returns one row per tag for a song, songs with multiple tags were duplicated in the SQL result set.
-   **Fix and Side-Effect Check**: Removed the redundant `outerjoin`. Since tags are already loaded via a `lazy="subquery"` relationship on the `Song` model, the join was unnecessary for the current feature set. Side-effect check: Verified that songs still correctly show their tags in the search results via a Playwright verification script.

### Issue #4: Missing notification for song ratings
-   **Reproduction**: Rated a song shared by a friend and checked that friend's `/notifications` endpoint. No notification was found.
-   **Navigation Strategy**: Compared `notification_service.py:add_to_playlist` (which sends notifications) with `rate_song`. Traced the flow from `routes/songs.py:rate()`.
-   **Root Cause**: The `rate_song` function implemented the rating logic but lacked the call to `create_notification`. It failed to satisfy the Docstring Contract implied by the "social music app" description.
-   **Fix and Side-Effect Check**: Added a call to `create_notification` inside `rate_song`, targeted at `song.shared_by`. Side-effect check: Confirmed that users do not receive notifications for rating their own songs to avoid self-notification spam.

### Issue #5: The last song in a playlist never shows up
-   **Reproduction**: Created a playlist with 3 songs and fetched `/playlists/<id>/songs`. Only 2 songs were returned.
-   **Navigation Strategy**: Traced `GET /playlists/<id>/songs` to `playlist_service.py:get_playlist_songs`. Inspected the return statement.
-   **Root Cause**: The function was returning `songs[:-1]`. This Python slice explicitly excludes the last element of the list, violating the Docstring Contract which promises "all songs in the playlist."
-   **Fix and Side-Effect Check**: Removed the `[:-1]` slice. Side-effect check: Verified that fixing the range logic didn't break the `added_by` attribution or ordering, which are handled by the query itself.
