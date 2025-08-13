from content_filtering import prepare_song_vectors, compute_user_avg_vector
from collaborative_filtering import load_user_item_matrix
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import MongoClient
import numpy as np

def recommend_hybrid_weighted(user_name, uri="mongodb://localhost:27017/", content_weight=0.8, collab_weight=0.2):
    # 1. 콘텐츠 벡터 및 사용자 벡터 준비
    _, _, song_vectors, music_data = prepare_song_vectors(uri)
    user_vector, liked_titles = compute_user_avg_vector(user_name, song_vectors, uri)
    music_dict = {song["title"]: song for song in music_data}

    # 2. 콘텐츠 기반 유사도 계산
    content_scores = {}
    for title, vec in song_vectors.items():
        if title in liked_titles:
            continue
        vec = vec.reshape(1, -1)
        score = cosine_similarity(user_vector.reshape(1, -1), vec)[0][0]
        content_scores[title] = score

    # 3. 협업 기반 유사도 계산 (유사 사용자들이 좋아한 곡 빈도)
    user_ids, all_titles, matrix, user_likes = load_user_item_matrix(uri)
    if user_name not in user_ids:
        raise ValueError(f"사용자 {user_name}가 존재하지 않습니다.")
    
    user_idx = user_ids.index(user_name)
    target_vec = matrix[user_idx].reshape(1, -1)
    similarities = [
        (uid, cosine_similarity(target_vec, matrix[i].reshape(1, -1))[0][0])
        for i, uid in enumerate(user_ids) if uid != user_name
    ]
    similarities.sort(key=lambda x: x[1], reverse=True)
    top_users = [uid for uid, _ in similarities[:2]]  # Top-K = 2

    collab_counter = {}
    for uid in top_users:
        for title in user_likes[uid]:
            if title not in liked_titles:
                collab_counter[title] = collab_counter.get(title, 0) + 1

    # 4. 콘텐츠/협업 점수 합산 → 최종 점수
    all_titles_set = set(content_scores.keys()) | set(collab_counter.keys())
    results = []
    for title in all_titles_set:
        content_score = content_scores.get(title, 0.0)
        collab_score = collab_counter.get(title, 0.0)
        final_score = content_weight * content_score + collab_weight * collab_score

        if title in music_dict:
            song = music_dict[title]
            results.append({
                "title": title,
                "artist": song.get("artist", "unknown"),
                "duration": song.get("duration", "--"),
                "youtube_url": song.get("youtube_url", ""),
                "final_score": final_score
            })

    # 5. 정렬 및 Top 10 추출
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results[:10]