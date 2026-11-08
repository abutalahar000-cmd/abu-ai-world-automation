import os
import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("YOUTUBE_API_KEY")
REGION = "US"
SEARCH_QUERY = "technology science educational videos for kids"

def youtube_api(endpoint, params):
    params["key"] = API_KEY
    url = (
        "https://www.googleapis.com/youtube/v3/"
        + endpoint + "?"
        + urllib.parse.urlencode(params)
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read())

def research_topics():
    if not API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is not configured")

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=90)
    ).isoformat().replace("+00:00", "Z")

    results = youtube_api("search", {
        "part": "snippet",
        "type": "video",
        "q": SEARCH_QUERY,
        "regionCode": REGION,
        "relevanceLanguage": "en",
        "order": "viewCount",
        "publishedAfter": published_after,
        "maxResults": 15
    })

    video_ids = [
        item["id"]["videoId"]
        for item in results.get("items", [])
    ]

    if not video_ids:
        raise RuntimeError("No research videos found")

    stats = youtube_api("videos", {
        "part": "statistics,contentDetails,snippet",
        "id": ",".join(video_ids)
    })

    videos = []

    for item in stats.get("items", []):
        data = item["statistics"]
        videos.append({
            "title": item["snippet"]["title"],
            "views": int(data.get("viewCount", 0)),
            "likes": int(data.get("likeCount", 0)),
            "comments": int(data.get("commentCount", 0)),
            "video_id": item["id"]
        })

    videos.sort(key=lambda x: x["views"], reverse=True)

    plan = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "research_query": SEARCH_QUERY,
        "top_research": videos[:10],
        "next_step": "Generate an original video topic from research"
    }

    with open("topic_plan.json", "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)

    print("Research completed!")
    for video in videos[:5]:
        print(video["title"], "| Views:", video["views"])

if __name__ == "__main__":
    print("Abu AI Autonomous Agent Started")
    research_topics()
    
