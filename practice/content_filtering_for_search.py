from pymongo import MongoClient
import numpy as np
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity
import sys
sys.stdout.reconfigure(encoding='utf-8')

# -----------------------------
def load_music_data(uri, db_name, collection_name):
    client = MongoClient(uri)
    db = client[db_name]
    collection = db[collection_name]
    data = list(collection.find({}, {"_id": 0}))
    print(f"불러온 곡 개수: {len(data)}")
    return data

def make_string(text):
    return " ".join(text) if isinstance(text, list) else str(text)

# -----------------------------
def train_word2vec(music_data, vector_size=100):
    sentences = []
    for song in music_data:
        lyrics = make_string(song.get("lyrics", "")).lower()
        words = lyrics.split()
        if words:
            sentences.append(words)

    if not sentences:
        raise ValueError('가사 문장이 없음')

    model = Word2Vec(sentences, vector_size=vector_size, window=5, min_count=1, workers=4, epochs=5)
    return model

def get_lyrics_vector(lyrics, model):
    words = make_string(lyrics).lower().split()
    word_vectors = [model.wv[word] for word in words if word in model.wv]
    if word_vectors:
        return np.mean(word_vectors, axis=0)
    else:
        return np.zeros(model.vector_size)

def make_song_vectors(music_data, model):
    vectors = {}
    for song in music_data:
        title = song.get("title", "")
        if not title:
            continue
        lyrics_vec = get_lyrics_vector(song.get("lyrics", ""), model)
        vectors[title] = lyrics_vec
    return vectors

# -----------------------------
def get_query_vector(query_text, model):
    words = make_string(query_text).lower().split()
    word_vecs = [model.wv[word] for word in words if word in model.wv]
    if not word_vecs:
        raise ValueError("입력 문장에서 유효한 단어가 없습니다.")
    return np.mean(word_vecs, axis=0)

def recommend_by_query_vector(query_vec, song_vectors, music_data, top_n=5):
    query_vec = query_vec.reshape(1, -1)
    similarities = []

    for song in music_data:
        title = song.get("title", "")
        if not title or title not in song_vectors:
            continue

        song_vec = song_vectors[title].reshape(1, -1)
        sim = cosine_similarity(query_vec, song_vec)[0][0]
        similarities.append((title, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_n]

# -----------------------------
if __name__ == "__main__":
    uri = "mongodb://localhost:27017/"
    db_name = "music"
    collection_name = "music"

    music_data = load_music_data(uri, db_name, collection_name)
    model = train_word2vec(music_data)
    song_vectors = make_song_vectors(music_data, model)

    user_query = input("\n듣고 싶은 분위기를 입력하세요 (예: 비 오는 날 듣기 좋은 노래):\n> ")

    try:
        query_vector = get_query_vector(user_query, model)
        recommendations = recommend_by_query_vector(query_vector, song_vectors, music_data, top_n=5)

        print(f"\n'{user_query}'에 어울리는 추천곡:")
        for idx, (title, sim) in enumerate(recommendations, 1):
            print(f"{idx}. {title} (유사도: {sim:.4f})")

    except ValueError as e:
        print(f"\n[오류] {e}")
