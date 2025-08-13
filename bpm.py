import requests
import json
import time
import os
import base64

# Spotify Client ID / Secret 직접 입력
CLIENT_ID = "e1f75d180bd5485098b6fb0c5bc1ef94"
CLIENT_SECRET = "1d4d167351d84546852fd27c05adbfb4"

# 1. Spotify 인증 토큰
def get_token():
    url = "https://accounts.spotify.com/api/token"
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    res = requests.post(url, headers=headers, data=data)
    return res.json().get("access_token")

# 2. 제목+아티스트로 track_id 검색
def search_track_id(song_title, artist_name, token):
    query = f"{song_title} {artist_name}".strip()
    url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)
    items = res.json().get("tracks", {}).get("items", [])

    if items:
        print(f"🎯 검색 성공: {items[0]['name']} / {items[0]['artists'][0]['name']}")
        return items[0]["id"]
    else:
        print(f"⚠️ 검색 실패: '{query}'")
        return None

# 3. track_id로 BPM(tempo) 추출
def get_bpm(track_id, token):
    url = f"https://api.spotify.com/v1/audio-features/{track_id}"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers)

    if res.status_code == 200:
        data = res.json()
        tempo = data.get("tempo")
        print(f"   🎧 BPM 추출 성공 → tempo: {tempo}")
        return tempo
    else:
        print(f"   ❌ BPM 요청 실패: {res.status_code} / {res.text}")
        return None

# 4. JSON 파일 업데이트
def update_bpm_in_json(input_file, output_file, max_count=None):
    with open(input_file, 'r', encoding='utf-8') as f:
        songs = json.load(f)

    if max_count:
        songs = songs[:max_count]

    token = get_token()

    for idx, song in enumerate(songs):
        title = song.get("title", "").strip()
        artist = song.get("artist", "").strip()

        if not title:
            song["bpm"] = "제목 없음"
            continue

        print(f"\n🎵 [{idx + 1}/{len(songs)}] 처리 중: {title} - {artist}")
        try:
            track_id = search_track_id(title, artist, token)
            if track_id:
                bpm = get_bpm(track_id, token)
                song["bpm"] = round(bpm, 2) if bpm else "BPM 정보 없음"
            else:
                song["bpm"] = "BPM 정보 없음"
        except Exception as e:
            print("   ⚠️ 에러 발생:", e)
            song["bpm"] = "BPM 정보 없음"

        time.sleep(0.5)  # 속도 제한 방지

        # 🔄 10곡마다 중간 저장
        if (idx + 1) % 10 == 0:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(songs, f, ensure_ascii=False, indent=4)
            print(f"💾 중간 저장 완료 ({idx + 1}곡)")

    # 🔚 마지막 저장
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(songs, f, ensure_ascii=False, indent=4)

    print(f"\n✅ 전체 완료! → {output_file}")

# 🔸 실행 설정
input_json_path = "C:\\Users\\xogus\\OneDrive\\바탕 화면\\vscfile\\capstonedesign\\music_music2.json"
output_json_path = "output_songs_with_bpm.json"

# 🔹 테스트용: 최대 20곡만 처리 (None이면 전체)
update_bpm_in_json(input_json_path, output_json_path, max_count=20)
