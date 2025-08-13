from pymongo import MongoClient
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ---------- 1. Word2Vec & 벡터화 준비 ----------
def prepare_song_vectors(uri="mongodb://localhost:27017/"):
    client = MongoClient(uri)
    db = client["music"]
    music_data = list(db["music"].find({}, {"_id": 0}))

    # 전처리된 리스트 형태의 가사 사용
    sentences = [song["lyrics"] for song in music_data if isinstance(song.get("lyrics"), list)]
    model = Word2Vec(sentences, vector_size=100, window=5, min_count=1, sg=1, epochs=10)

    # 전처리된 장르 리스트 사용
    all_genres = sorted(set(g for song in music_data for g in song.get("genres", [])))

    def get_lyrics_vector(lyrics):
        vectors = [model.wv[word] for word in lyrics if word in model.wv]
        return np.mean(vectors, axis=0) if vectors else np.zeros(model.vector_size)

    def get_genre_vector(genres):
        vec = np.zeros(len(all_genres))
        for g in genres:
            if g in all_genres:
                vec[all_genres.index(g)] = 1
        return vec

    song_vectors = {}
    for song in music_data:
        title = song.get("title")
        if not title:
            continue
        lyrics_vec = get_lyrics_vector(song.get("lyrics", []))
        genre_vec = get_genre_vector(song.get("genres", []))
        song_vectors[title] = np.concatenate([lyrics_vec, genre_vec])

    return model, all_genres, song_vectors, music_data

# ---------- 2. 사용자 평균 벡터 계산 ----------
def compute_user_avg_vector(user_name, song_vectors, uri="mongodb://localhost:27017/"):
    client = MongoClient(uri)
    user_db = client["user"]

    if user_name not in user_db.list_collection_names():
        raise ValueError(f"사용자 {user_name}가 존재하지 않습니다.")

    collection = user_db[user_name]
    liked_titles = [doc["title"] for doc in collection.find({}, {"_id": 0})]

    vectors = [song_vectors[title] for title in liked_titles if title in song_vectors]
    if not vectors:
        raise ValueError("유효한 곡 벡터가 없습니다.")

    avg_vector = np.mean(vectors, axis=0)
    return avg_vector, liked_titles

# ---------- 3. 추천 함수 ----------
def recommend_top_n_songs(user_vector, song_vectors, music_data, liked_titles, top_n=10, start_year=None, end_year=None):
    liked_artists = {song.get("artist") for song in music_data if song.get("title") in liked_titles}
    seen_titles = set()
    results = []

    for song in music_data:
        title = song.get("title")
        artist = song.get("artist")
        release_year = song.get("release_year")

        if not title or title in liked_titles or title in seen_titles or title not in song_vectors:
            continue

        if start_year and end_year:
            try:
                year = int(release_year)
                if not (start_year <= year <= end_year):
                    continue
            except:
                continue

        vec = song_vectors[title].reshape(1, -1)
        sim = cosine_similarity(user_vector.reshape(1, -1), vec)[0][0]
        artist_bonus = 0.05 if artist in liked_artists else 0.0
        final_score = sim + artist_bonus

        results.append((final_score, {
            "title": title,
            "artist": artist,
            "duration": song.get("duration", "--"),
            "youtube_url": song.get("youtube_url", "")
        }))
        seen_titles.add(title)

    # 유사도 높은 순으로 정렬하고 상위 N개 반환
    results.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in results[:top_n]]
