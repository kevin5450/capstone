import json, requests, isodate, time, os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_youtube_duration(video_id):
    url = "https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "contentDetails", "id": video_id, "key": API_KEY}
    try:
        res = requests.get(url, params=params).json()
        iso_duration = res["items"][0]["contentDetails"]["duration"]
        seconds = isodate.parse_duration(iso_duration).total_seconds()
        return f"{int(seconds // 60)}:{int(seconds % 60):02d}"
    except:
        return "--"

def get_youtube_info(title, artist):
    query = f"{title} {artist} 공식 뮤직비디오"
    url = "https://www.googleapis.com/youtube/v3/search"
    params = {"part": "snippet", "q": query, "key": API_KEY, "maxResults": 3, "type": "video"}
    res = requests.get(url, params=params).json()
    for item in res.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}", get_youtube_duration(video_id)
    return "검색 실패", "--"

# ----- JSON 불러오기 -----
with open("C:\\Users\\xogus\\OneDrive\\바탕 화면\\vscfile\\capstonedesign\\music_music2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ----- 유튜브 매핑 -----
for i, item in enumerate(data[:10]):
    item.pop("_id", None)  # MongoDB ID 제거
    title, artist = item.get("title"), item.get("artist")
    if not title or not artist:
        continue
    print(f"[{i+1}] 검색: {title} - {artist}")
    url, duration = get_youtube_info(title, artist)
    item["youtube_url"], item["duration"] = url, duration
    time.sleep(1)

# ----- 저장 -----
with open("music_with_youtube.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("저장 완료: music_with_youtube.json")
