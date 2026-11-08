import os
import json
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("YOUTUBE_API_KEY")

CHANNEL_NAME = "Abu AI World"
MAIN_CHARACTER = "Abu AI"
REGION = "US"

SEARCH_QUERY = (
    "science technology space universe "
    "human body artificial intelligence robotics "
    "scientific discoveries inventions education"
)

CATEGORIES = [
    "Science",
    "Space and Universe",
    "Human Body",
    "Artificial Intelligence",
    "Robotics",
    "Technology",
    "Inventions",
    "Scientific Discoveries",
    "Earth and Nature",
    "Physics and Chemistry"
]


def youtube_api(endpoint, params):
    params["key"] = API_KEY

    url = (
        "https://www.googleapis.com/youtube/v3/"
        + endpoint + "?"
        + urllib.parse.urlencode(params)
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Abu-AI-Research-Agent/1.0"}
    )

    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"YouTube API error {error.code}: {details[:1000]}"
        ) from error


def research_videos():
    if not API_KEY:
        raise RuntimeError("YOUTUBE_API_KEY is missing")

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=90)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    search = youtube_api("search", {
        "part": "snippet",
        "type": "video",
        "q": SEARCH_QUERY,
        "regionCode": REGION,
        "relevanceLanguage": "en",
        "order": "viewCount",
        "publishedAfter": published_after,
        "maxResults": 25
    })

    video_ids = [
        item["id"]["videoId"]
        for item in search.get("items", [])
        if item.get("id", {}).get("videoId")
    ]

    if not video_ids:
        raise RuntimeError("No YouTube research videos found")

    details = youtube_api("videos", {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(video_ids)
    })

    videos = []

    for item in details.get("items", []):
        stats = item.get("statistics", {})
        snippet = item.get("snippet", {})

        views = int(stats.get("viewCount", 0))
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        engagement = (
            (likes + comments) / views * 100
            if views else 0
        )

        score = views * (1 + engagement / 100)

        videos.append({
            "title": snippet.get("title", ""),
            "channel": snippet.get("channelTitle", ""),
            "video_id": item["id"],
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_percent": round(engagement, 2),
            "performance_score": round(score, 2),
            "category": snippet.get("categoryId", "")
        })

    videos.sort(
        key=lambda video: video["performance_score"],
        reverse=True
    )

    return videos


def create_research_report(videos):
    best_videos = videos[:10]
    top_video = best_videos[0]

    report = {
        "channel": CHANNEL_NAME,
        "main_character": MAIN_CHARACTER,
        "audience": "All ages",
        "content_type": "Science, Education and Technology",
        "documentary_content": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "categories": CATEGORIES,
        "recommended_next_topic": top_video["title"],
        "reason": (
            "Selected using public video views, likes, "
            "comments and engagement."
        ),
        "top_research_videos": best_videos
    }

    with open(
        "topic_plan.json", "w", encoding="utf-8"
    ) as file:
        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("Abu AI Research completed!")

    print("Channel:", CHANNEL_NAME)
    print("Character:", MAIN_CHARACTER)
    print("Audience: All ages")
    print("Content: Science and Education")

    print("\nTop performing research videos:")

    for number, video in enumerate(best_videos[:5], 1):
        print(
            number,
            video["title"],
            "| Views:", video["views"],
            "| Likes:", video["likes"],
            "| Comments:", video["comments"]
        )

    print("\nRecommended next topic:")
    print(top_video["title"])


def main():
    print("Starting Abu AI Science Research Agent")

    videos = research_videos()
    create_research_report(videos)

    print("\nResearch finished successfully!")


if __name__ == "__main__":
    main()
    
