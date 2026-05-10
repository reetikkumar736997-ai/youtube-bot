import time
import requests
import os
import threading
from flask import Flask
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ============================
# 🌐 DUMMY WEB SERVER FOR RENDER
# ============================

app = Flask(__name__)

@app.route("/")
def home():
    return "YouTube Bot Running ✅"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ============================
# 🔧 SETTINGS
# ============================

YOUTUBE_API_KEYS = [
    os.getenv("YOUTUBE_API_KEY_1"),
    os.getenv("YOUTUBE_API_KEY_2"),
    os.getenv("YOUTUBE_API_KEY_3"),
    os.getenv("YOUTUBE_API_KEY_4"),
    os.getenv("YOUTUBE_API_KEY_5"),
    os.getenv("YOUTUBE_API_KEY_6"),
]

CHANNEL_URL = "https://www.youtube.com/channel/UCIAOlizjAwsPdwF2RIbyk1g"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

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
    print(f"🔁 Switched to API key #{current_key_index + 1}", flush=True)

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
        print(f"Telegram Error: {e}", flush=True)

# ============================
# 📺 FETCH STREAMS
# ============================

def get_all_upcoming_streams():
    while True:
        try:
            youtube = build(
                'youtube',
                'v3',
                developerKey=get_current_api_key()
            )

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
                    chat_id = info.get(
                        'liveStreamingDetails', {}
                    ).get('activeLiveChatId')

                    if chat_id:
                        streams.append({
                            "title": info['snippet']['title'],
                            "chat_id": chat_id
                        })

            return streams

        except HttpError as e:
            if "quotaExceeded" in str(e):
                print("⚠ Quota exceeded, switching key...", flush=True)
                switch_to_next_key()
            else:
                print(e, flush=True)
                time.sleep(10)

# ============================
# 🛰 MONITOR
# ============================

def monitor_single_stream():
    print("🔍 Streams fetch ho rahe hain...", flush=True)

    streams = get_all_upcoming_streams()

    selected_stream = None

    for s in streams:
        if "0066" in s["title"]:
            selected_stream = s
            break

    if not selected_stream:
        print("❌ Stream nahi mila", flush=True)
        time.sleep(60)
        return

    print(f"✅ Monitoring: {selected_stream['title']}", flush=True)

    youtube = build(
        'youtube',
        'v3',
        developerKey=get_current_api_key()
    )

    page_token = None

    # 🔥 duplicate messages stop
    processed_messages = set()

    while True:
        try:
            response = youtube.liveChatMessages().list(
                liveChatId=selected_stream['chat_id'],
                part='snippet,authorDetails',
                pageToken=page_token
            ).execute()

            for item in response.get('items', []):

                message_id = item['id']

                # agar pehle aa chuka hai to skip
                if message_id in processed_messages:
                    continue

                processed_messages.add(message_id)

                author = item['authorDetails']['displayName']
                message = item['snippet']['displayMessage']

                print(f"{author}: {message}", flush=True)

                send_telegram_notification(
                    selected_stream['title'],
                    author,
                    message
                )

            page_token = response.get('nextPageToken')

        except HttpError as e:
            if "quotaExceeded" in str(e):
                switch_to_next_key()

                youtube = build(
                    'youtube',
                    'v3',
                    developerKey=get_current_api_key()
                )
            else:
                print(e, flush=True)

        time.sleep(CHAT_CHECK_INTERVAL)

# ============================
# 🚀 MAIN
# ============================

if __name__ == "__main__":

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    while True:
        monitor_single_stream()
