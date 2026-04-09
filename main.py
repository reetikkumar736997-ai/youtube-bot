import time
import requests
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================
# 🔧 MANUAL SETTINGS
# ============================

# 🔐 API keys Railway variables se aayengi
YOUTUBE_API_KEYS = [
    os.getenv("YOUTUBE_API_KEY_1"),
    os.getenv("YOUTUBE_API_KEY_2"),
    os.getenv("YOUTUBE_API_KEY_3"),
    os.getenv("YOUTUBE_API_KEY_4"),
    os.getenv("YOUTUBE_API_KEY_5"),
    os.getenv("YOUTUBE_API_KEY_6"),
]

# Channel URL
CHANNEL_URL = "https://www.youtube.com/channel/UCIAOlizjAwsPdwF2RIbyk1g"

# 🔐 Telegram details Railway se
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Refresh intervals
STREAM_REFRESH_INTERVAL = 10800
CHAT_CHECK_INTERVAL = 15

# ============================
# 🔁 API KEY HANDLER
# ============================

current_key_index = 0

def get_current_api_key():
    return YOUTUBE_API_KEYS[current_key_index]

def switch_to_next_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(YOUTUBE_API_KEYS)
    print(f"🔁 API key switched (#{current_key_index + 1})")

# ============================
# 📤 TELEGRAM
# ============================

def send_telegram_notification(stream_title, author, message):
    text = f"🔔 {stream_title}\n👤 {author}\n💬 {message}"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    try:
        requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text
        })
    except Exception as e:
        print(f"Telegram Error: {e}")

# ============================
# 📺 FETCH STREAMS
# ============================

def get_all_upcoming_streams():
    while True:
        try:
            youtube = build('youtube', 'v3', developerKey=get_current_api_key())
            channel_id = CHANNEL_URL.split('/')[-1]

            search = youtube.search().list(
                part='id',
                channelId=channel_id,
                eventType='upcoming',
                type='video',
                maxResults=10
            ).execute()

            streams = []

            for item in search.get('items', []):
                video_id = item['id']['videoId']

                video = youtube.videos().list(
                    part='snippet,liveStreamingDetails',
                    id=video_id
                ).execute()

                if video['items']:
                    info = video['items'][0]
                    chat_id = info.get('liveStreamingDetails', {}).get('activeLiveChatId')

                    if chat_id:
                        streams.append({
                            "title": info['snippet']['title'],
                            "chat_id": chat_id
                        })

            return streams

        except HttpError as e:
            if "quotaExceeded" in str(e):
                print("⚠ Quota exceeded, switching key...")
                switch_to_next_key()
            else:
                print(e)
                time.sleep(10)

# ============================
# 🛰 MONITOR STREAM
# ============================

def monitor_single_stream():
    print("🔍 Streams fetch ho rahe hain...")

    streams = get_all_upcoming_streams()

    selected_stream = None
    for s in streams:
        if "0066" in s["title"]:
            selected_stream = s
            break

    if not selected_stream:
        print("❌ Target stream nahi mila, retry...")
        time.sleep(60)
        return

    print(f"✅ Monitoring: {selected_stream['title']}")

    youtube = build('youtube', 'v3', developerKey=get_current_api_key())
    page_token = None
    last_refresh = time.time()

    while True:
        try:
            if time.time() - last_refresh > STREAM_REFRESH_INTERVAL:
                print("🔄 Refreshing stream...")
                return

            response = youtube.liveChatMessages().list(
                liveChatId=selected_stream['chat_id'],
                part='snippet,authorDetails',
                pageToken=page_token
            ).execute()

            for item in response.get('items', []):
                author = item['authorDetails']['displayName']
                message = item['snippet']['displayMessage']

                print(f"📩 {author}: {message}")
                send_telegram_notification(selected_stream['title'], author, message)

            page_token = response.get('nextPageToken')

        except HttpError as e:
            if "quotaExceeded" in str(e):
                switch_to_next_key()
                youtube = build('youtube', 'v3', developerKey=get_current_api_key())
            else:
                print(e)

        except Exception as e:
            print(f"⚠ Error: {e}")

        time.sleep(CHAT_CHECK_INTERVAL)

# ============================
# 🚀 MAIN LOOP
# ============================

if __name__ == "__main__":
    while True:
        try:
            print("🚀 Bot start ho gaya...")
            monitor_single_stream()
        except Exception as e:
            print(f"❌ Crash: {e}")
            time.sleep(10)
