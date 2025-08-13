import json

# ---------- 예시 JSON 불러오기 ----------
with open("C:\\Users\\xogus\\OneDrive\\바탕 화면\\vscfile\\capstonedesign\\output_final2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ---------- 전처리 함수 ----------
def clean_lyrics(data):
    for song in data:
        if "lyrics" in song and isinstance(song["lyrics"], list):
            song["lyrics"] = [line for line in song["lyrics"] if line.strip() != ""]
    return data

# ---------- 전처리 적용 ----------
cleaned_data = clean_lyrics(data)

# ---------- 결과 저장 ----------
with open("cleaned_song_data.json", "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

print("빈 가사 줄이 제거된 JSON 파일을 저장했습니다.")
