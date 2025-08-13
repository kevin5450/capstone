import json
import yt_dlp
import time
import os

INPUT_PATH = "C:\\Users\\xogus\\OneDrive\\바탕 화면\\vscfile\\capstonedesign\\output_final.json"
OUTPUT_PATH = "output_final2.json"
PARTIAL_PATH = "output_partial2.json"

# -------- 유튜브 정보 추출 --------
def get_youtube_info(title, artist):
    query = f"ytsearch1:{title} {artist} 공식 뮤직비디오"
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "format": "bestaudio/best",
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(query, download=False)
            video = result['entries'][0]
            url = video['webpage_url']
            seconds = video['duration']
            duration = f"{int(seconds // 60)}:{int(seconds % 60):02d}"
            return url, duration
    except Exception as e:
        return "검색 실패", "--"

# -------- JSON 파일 불러오기 --------
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    songs = json.load(f)

# -------- 유튜브 정보 추가 --------
for i, song in enumerate(songs):
    title = song.get("title")
    artist = song.get("artist")

    if not title or not artist:
        continue
    if "youtube_url" in song and song["youtube_url"] != "검색 실패":
        continue

    print(f"[{i+1}] 검색 중: {title} - {artist}")
    url, duration = get_youtube_info(title, artist)
    song["youtube_url"] = url
    song["duration"] = duration

    if (i + 1) % 100 == 0:
        with open(PARTIAL_PATH, "w", encoding="utf-8") as f:
            json.dump(songs, f, indent=2, ensure_ascii=False)
        print(f"  💾 {i+1}곡까지 저장됨 → {PARTIAL_PATH}")

    time.sleep(1.5)

# -------- 최종 저장 --------
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(songs, f, indent=2, ensure_ascii=False)

print(f"\n1차 저장 완료: {OUTPUT_PATH}")

# ===============================
#  🔁 검색 실패한 곡 재시도
# ===============================
failed_songs = [song for song in songs if song.get("youtube_url") == "검색 실패"]
print(f"\n🔍 검색 실패 곡 수: {len(failed_songs)} → 재시도 시작")

retry_success_count = 0
for i, song in enumerate(failed_songs):
    title = song.get("title")
    artist = song.get("artist")
    print(f"[재시도 {i+1}] {title} - {artist}")
    url, duration = get_youtube_info(title, artist)

    if url != "검색 실패":
        song["youtube_url"] = url
        song["duration"] = duration
        retry_success_count += 1
    time.sleep(1.5)

# 다시 반영된 곡들을 기존 리스트에 업데이트
for song in songs:
    for retry_song in failed_songs:
        if song["title"] == retry_song["title"] and song["artist"] == retry_song["artist"]:
            song.update(retry_song)

# -------- 최종 저장 --------
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(songs, f, indent=2, ensure_ascii=False)

print(f"\n✅ 재시도 완료: 총 {len(failed_songs)}곡 중 {retry_success_count}곡 추가 성공")
print(f"📁 최종 결과 저장됨 → {OUTPUT_PATH}")
