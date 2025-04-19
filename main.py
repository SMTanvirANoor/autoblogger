import os
import json
import requests
import random
import html
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# === CONFIG ===
NUM_POSTS_PER_RUN = 1  # Will run 3x/day
BLOGGER_SCOPES = ['https://www.googleapis.com/auth/blogger']
UNSPLASH_ACCESS_KEY = 'M3h4wTk6VqIEArVWzc2o0MsU3rWVuGqukZtgq59Utus'  # Get from https://unsplash.com/developers
OPENROUTER_API_KEY = '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'  # Get from https://openrouter.ai/
BLOG_ID = '8035062769203219427'  # Get this from Blogger dashboard URL or API
LANG = 'en'

# === 1. Get Trending Topic ===
def get_trending_topic():
    rss_url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    response = requests.get(rss_url)
    titles = [line.split("<title>")[1].split("</title>")[0]
              for line in response.text.splitlines() if "<title>" in line]
    topics = titles[2:]  # Skip Google Trends branding
    return random.choice(topics) if topics else "Interesting News Today"

# === 2. Generate Post with AI ===
def generate_post(topic):
    prompt = f"Write a 600-word blog post in HTML format about '{topic}'. Make it informative and engaging."
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }
    res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    content = res.json()["choices"][0]["message"]["content"]
    return content

# === 3. Get Image from Unsplash ===
def fetch_unsplash_image(topic):
    url = f"https://api.unsplash.com/photos/random?query={topic}&client_id={UNSPLASH_ACCESS_KEY}"
    res = requests.get(url).json()
    return res.get("urls", {}).get("regular", "")

# === 4. Post to Blogger ===
def authenticate_blogger():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', BLOGGER_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', BLOGGER_SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('blogger', 'v3', credentials=creds)

def post_to_blogger(service, title, html_content):
    body = {
        "kind": "blogger#post",
        "title": title,
        "content": html_content
    }
    service.posts().insert(blogId=BLOG_ID, body=body, isDraft=False).execute()

# === MAIN RUN ===
def main():
    service = authenticate_blogger()
    for _ in range(NUM_POSTS_PER_RUN):
        topic = get_trending_topic()
        content = generate_post(topic)
        image_url = fetch_unsplash_image(topic)
        if image_url:
            content = f'<img src="{image_url}" style="width:100%;height:auto;"><br><br>' + content
        post_to_blogger(service, topic, content)
        print(f"[{datetime.now()}] Posted: {topic}")

if __name__ == '__main__':
    main()
