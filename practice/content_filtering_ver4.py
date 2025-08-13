from pymongo import MongoClient
import numpy as np
from gensim.models import Word2Vec
import re
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

def clean_lyrics(lyrics):
    lyrics = make_string(lyrics).lower()
    lyrics = re.sub(r"[^가-힣a-zA-Z\s]", "", lyrics)
    return lyrics

def train_word2vec(music_data, vector_size=100):
    sentences = []
    for song in music_data:
        lyrics = clean_lyrics(song.get("lyrics", ""))
        words = lyrics.split()
        if words:
            sentences.append(words)
    if not sentences:
        raise ValueError('가사 문장이 없음')
    model = Word2Vec(sentences, vector_size=vector_size, window=5, min_count=1, workers=4, epochs=10)
    return model

# -----------------------------
stopwords = {
    "때", "할때", "가", "은", "는", "이", "의", "에", "를", "을", "도", "과", "와", "한", "또", "좀", "더",
    "까지", "만", "으로", "하고", "에서", "the", "is", "are", "to", "and", "a", "of", "on", "in", "for",
    "with", "by", "at", "an", "it", "be", "as", "this", "that"
}

def extract_keywords_simple(text):
    text = text.lower()
    text = re.sub(r"[^가-힣a-zA-Z\s]", "", text)
    words = text.split()
    keywords = [w for w in words if w not in stopwords and len(w) >= 2]
    return keywords

# -----------------------------
def fast_cosine_similarity(vec1, vec2):
    dot = np.dot(vec1, vec2)
    norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    return dot / norm if norm != 0 else 0.0

def get_query_vector_by_sentence(query_text, model):
    text = clean_lyrics(query_text)
    words = [w for w in text.split() if w not in stopwords and w in model.wv]
    if not words:
        return None
    return np.mean([model.wv[w] for w in words], axis=0)

def mean_vector_similarity_from_vector(query_vector, lyrics, model, max_lyrics_words=100):
    if query_vector is None:
        return 0.0
    lyrics_words = clean_lyrics(lyrics).split()[:max_lyrics_words]
    lyrics_vecs = [model.wv[word] for word in lyrics_words if word in model.wv]
    if not lyrics_vecs:
        return 0.0
    lyrics_mean = np.mean(lyrics_vecs, axis=0)
    return fast_cosine_similarity(query_vector, lyrics_mean)

def penalize_irrelevant_song(query_keywords, lyrics, original_score):
    lyrics_words = set(clean_lyrics(lyrics).split())
    overlap = lyrics_words & set(query_keywords)
    if not overlap:
        return original_score * 0.9
    return original_score

def recommend_by_query_text(query_text, music_data, model, top_n=5):
    query_vec = get_query_vector_by_sentence(query_text, model)
    query_keywords = extract_keywords_simple(query_text)
    results = []
    seen = set()
    for song in music_data:
        title = song.get("title", "")
        artist = song.get("artist", "")
        unique_id = f"{title}-{artist}"
        if unique_id in seen:
            continue
        seen.add(unique_id)

        lyrics = song.get("lyrics", "")
        sim = mean_vector_similarity_from_vector(query_vec, lyrics, model)
        sim = penalize_irrelevant_song(query_keywords, lyrics, sim)

        results.append((title, artist, lyrics, sim))
    results.sort(key=lambda x: x[3], reverse=True)
    return results[:top_n], query_keywords

# -----------------------------
if __name__ == "__main__":
    uri = "mongodb://localhost:27017/"
    db_name = "music"
    collection_name = "music"

    music_data = load_music_data(uri, db_name, collection_name)
    model = train_word2vec(music_data)

    user_query = input("\n듣고 싶은 분위기를 입력하세요 (예: 여행 중 차 안에서):\n> ").strip()
    if not user_query:
        print("[오류] 유효한 입력 문장이 없습니다.")
    else:
        recommendations, query_keywords = recommend_by_query_text(user_query, music_data, model, top_n=5)

        print(f"\n'{user_query}'에 어울리는 추천곡:")
        for idx, (title, artist, lyrics, sim) in enumerate(recommendations, 1):
            lyrics_words = clean_lyrics(lyrics).split()[:100]
            preview = " ".join(lyrics_words[:15]) + "..."

            top_keywords = []
            for word in lyrics_words:
                if word in model.wv:
                    for q in query_keywords:
                        if q in model.wv:
                            score = fast_cosine_similarity(model.wv[q], model.wv[word])
                            if score > 0.75:
                                top_keywords.append(word)
            top_keywords = list(dict.fromkeys(top_keywords))[:3]

            print(f"{idx}. {title} - {artist} (유사도: {sim:.4f})")
            print(f"   가사 일부: {preview}")
            print(f"   유사한 핵심 단어: {', '.join(top_keywords) if top_keywords else '없음'}\n")
