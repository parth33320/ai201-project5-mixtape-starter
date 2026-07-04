import asyncio
import requests
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        # Create a context that records video
        context = await browser.new_context(record_video_dir="tests/playwright/videos/")
        page = await context.new_page()

        # 1. Find a song and its sharer from the search endpoint
        search_resp = requests.get("http://localhost:5000/songs/search?q=Midnight Drive").json()
        song = search_resp['results'][0]
        song_id = song['id']
        sharer_id = song['shared_by']

        # To get the rater, I need a valid user ID.
        # Since I can't look up by username easily without the ID,
        # I'll find another song shared by someone else and use that sharer as the rater.
        search_resp_2 = requests.get("http://localhost:5000/songs/search?q=Block Party").json()
        rater_id = search_resp_2['results'][0]['shared_by']

        # Get rater info for verification message
        rater_info = requests.get(f"http://localhost:5000/users/{rater_id}").json()
        rater_username = rater_info['username']

        print(f"Rater: {rater_username} ({rater_id})")
        print(f"Song: {song['title']} (Sharer ID: {sharer_id})")

        # 2. Rate the song via API
        rate_resp = requests.post(f"http://localhost:5000/songs/{song_id}/rate", json={
            "user_id": rater_id,
            "score": 5
        })
        assert rate_resp.status_code == 201
        print("Rated song successfully.")

        # 3. Check notifications for the sharer
        await page.goto(f"http://localhost:5000/users/{sharer_id}/notifications")

        # Wait for the content to be visible (it's JSON)
        content = await page.content()
        print("Notification content retrieved.")

        # Check if the notification is present in the text
        if f"{rater_username} rated your song" in content:
            print("SUCCESS: Notification found!")
        else:
            print("FAILURE: Notification not found!")
            print(f"Content was: {content}")
            await browser.close()
            exit(1)

        # Take a screenshot
        await page.screenshot(path="tests/playwright/notification_verification.png")

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(verify())
