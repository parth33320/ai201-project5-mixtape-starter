# Mixtape Bug Hunt Slices

## Tracer Bullets

### Slice 1: Fix Streak Reset Bug (#1)
- **What**: Remove Sunday exception in `streak_service.py`.
- **Status**: Completed.
- **Verification**: Regression test `tests/test_streaks.py` and Playwright video.

### Slice 2: Fix Feed Threshold Bug (#2)
- **What**: Update `RECENT_THRESHOLD` to 10 minutes in `feed_service.py`.
- **Status**: Completed.
- **Verification**: Regression test `tests/test_feed_threshold.py` and Playwright video.

### Slice 3: Fix Search Duplicates Bug (#3)
- **What**: Remove redundant `outerjoin` in `search_service.py`.
- **Status**: Completed.
- **Verification**: Regression test `tests/test_search_duplicates.py` and Playwright video.

### Slice 4: Fix Notification Missing Bug (#4)
- **What**: Add notification logic to `rate_song` in `notification_service.py`.
- **Status**: Completed.
- **Verification**: Regression test `tests/test_notifications.py` and Playwright video.

### Slice 5: Fix Playlist Position Bug (#5)
- **What**: Remove incorrect slicing in `playlist_service.py`.
- **Status**: Completed.
- **Verification**: Regression test `tests/test_playlist_songs.py` and Playwright video.

### Slice 6: Regression Test Suite
- **What**: Implement comprehensive tests for all 5 bugs hitting local server.
- **Status**: Completed.
- **Verification**: All tests green.
