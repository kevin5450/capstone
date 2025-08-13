import json
from collections import Counter
import sys

input_file = r"C:\Users\xogus\OneDrive\바탕 화면\music.music2.json"
output_file = r"C:\Users\xogus\OneDrive\바탕 화면\music_converted2.json"

genre_counter = Counter()

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)

for song in data:
    genres = song.get("genre", [])

    # ✅ 문자열이면 리스트로 변환
    if isinstance(genres, str):
        genres = [genres]

    for g in genres:
        if isinstance(g, str) and g.strip():
            genre_counter[g.strip()] += 1

# 그대로 저장
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 한글 출력
sys.stdout.reconfigure(encoding='utf-8')

print("🎧 장르별 곡 수:")
for genre, count in genre_counter.most_common():
    print(f"{genre}: {count}곡")
