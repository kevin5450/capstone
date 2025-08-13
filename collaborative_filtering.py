from pymongo import MongoClient
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# 1. 사용자-아이템 행렬 생성
def load_user_item_matrix(uri):
    client = MongoClient(uri)
    db = client["user"]
    user_ids = db.list_collection_names()

    user_likes = {}
    all_titles = set()

    for user_id in user_ids:
        collection = db[user_id]
        titles = [doc["title"] for doc in collection.find({}, {"_id": 0}) if "title" in doc]
        user_likes[user_id] = set(titles)
        all_titles.update(titles)

    all_titles = sorted(all_titles)
    matrix = np.zeros((len(user_ids), len(all_titles)))
    title_idx = {title: i for i, title in enumerate(all_titles)}

    for i, user_id in enumerate(user_ids):
        for title in user_likes[user_id]:
            matrix[i][title_idx[title]] = 1

    return user_ids, all_titles, matrix, user_likes

# 2. 협업 필터링 추천
def recommend_user_cf(target_user, user_ids, all_titles, matrix, user_likes, music_data, top_k=2):
    if target_user not in user_ids:
        raise ValueError(f"사용자 {target_user}가 존재하지 않습니다.")

    user_idx = user_ids.index(target_user)
    target_vector = matrix[user_idx].reshape(1, -1)

    # 유사도 계산
    similarities = [
        (uid, cosine_similarity(target_vector, matrix[i].reshape(1, -1))[0][0])
        for i, uid in enumerate(user_ids) if uid != target_user
    ]
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_users = [uid for uid, _ in similarities[:top_k]]

    # 추천 곡 후보 = 유사 유저가 좋아한 곡 - 내가 이미 들은 곡
    target_likes = user_likes[target_user]
    recommended_titles = set()
    for uid in top_users:
        recommended_titles.update(user_likes[uid])
    recommendations = recommended_titles - target_likes

    # music_data를 title 기준으로 dict 구성 (빠른 검색용)
    music_dict = {song["title"]: song for song in music_data}

    results = []
    for title in list(recommendations)[:10]:
        song = music_dict.get(title, {})
        results.append({
            "title": title,
            "artist": song.get("artist", "unknown"),
            "duration": song.get("duration", "--"),
            "youtube_url": song.get("youtube_url", "")
        })

    return results

# 3. 단독 실행 테스트
if __name__ == "__main__":
    uri = "mongodb://localhost:27017/"
    target_user = "최민호"

    client = MongoClient(uri)
    music_data = list(client["music"]["music"].find({}, {"_id": 0}))
    user_ids, all_titles, matrix, user_likes = load_user_item_matrix(uri)

    recommendations = recommend_user_cf(
        target_user, user_ids, all_titles, matrix, user_likes, music_data, top_k=2
    )

    print(f"\n[추천 결과] 사용자 '{target_user}'에게 추천:")
    for item in recommendations:
        print(f"- {item['title']} - {item['artist']} ({item['duration']})")

#Memory-Based User-User Collaborative Filtering 구현