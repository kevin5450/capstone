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

# -----------------------------
# 가사 정제 함수
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
stopwords = {"때", "할때", "가", "은", "는", "이", "의", "에", "를", "을", "도", "과", "와", "한", "또", "좀", "더", "까지", "만", "으로", "하고","에서",
             "듣기","좋은","노래", "is", "are", "to", "and", "a", "of", "on", "in", "for", "with", "by", "at", "an", "it", "be", "as", "this", "that"}

def extract_keywords_simple(text):
    text = text.lower()
    text = re.sub(r"[^가-힣a-zA-Z\s]", "", text)
    words = text.split()
    keywords = [w for w in words if w not in stopwords and len(w) >= 1]
    return keywords

# -----------------------------
def fast_cosine_similarity(vec1, vec2):
    dot = np.dot(vec1, vec2)
    norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    return dot / norm if norm != 0 else 0.0

def average_vector_similarity(query_vecs, lyrics_vecs):
    if not query_vecs or not lyrics_vecs:
        return 0.0
    q_mean = np.mean(query_vecs, axis=0)
    l_mean = np.mean(lyrics_vecs, axis=0)
    return fast_cosine_similarity(q_mean, l_mean)

def word_level_similarity(query_keywords, lyrics, model, top_k=3, max_lyrics_words=100):
    lyrics_words = clean_lyrics(lyrics).split()[:max_lyrics_words]
    lyrics_vecs = [model.wv[word] for word in lyrics_words if word in model.wv]
    query_vecs = [model.wv[word] for word in query_keywords if word in model.wv]

    if not lyrics_vecs or not query_vecs:
        return 0.0

    sims = []
    for qv in query_vecs:
        sim_scores = [fast_cosine_similarity(qv, lv) for lv in lyrics_vecs]
        sim_scores.sort(reverse=True)
        top_sim = np.mean(sim_scores[:top_k])
        sims.append(top_sim)

    word_level_score = np.mean(sims)
    avg_score = average_vector_similarity(query_vecs, lyrics_vecs)

    return 0.6 * word_level_score + 0.4 * avg_score

def title_bonus_score(query_keywords, title, model, threshold=0.8, bonus=0.1):
    title_words = clean_lyrics(title).split()
    for qw in query_keywords:
        for tw in title_words:
            if qw in model.wv and tw in model.wv:
                sim = fast_cosine_similarity(model.wv[qw], model.wv[tw])
                if sim >= threshold:
                    return bonus
    return 0.0

def recommend_by_query_words(query_keywords, music_data, model, top_n=5):
    results = []
    for song in music_data:
        title = song.get("title", "")
        lyrics = song.get("lyrics", "")
        sim = word_level_similarity(query_keywords, lyrics, model)

        bonus = title_bonus_score(query_keywords, title, model)
        sim_total = sim + bonus

        results.append((title, sim_total, bonus))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_n]

if __name__ == "__main__":
    uri = "mongodb://localhost:27017/"
    db_name = "music"
    collection_name = "music"

    music_data = load_music_data(uri, db_name, collection_name)
    model = train_word2vec(music_data)

    user_query = input("\n듣고 싶은 키워드를 입력하세요:\n> ")
    keywords = extract_keywords_simple(user_query)

    if not keywords:
        print("[오류] 유효한 키워드가 없습니다.")
    else:
        recommendations = recommend_by_query_words(keywords, music_data, model, top_n=20)

        print(f"\n'{user_query}'에 어울리는 추천곡 (사용된 키워드: {', '.join(keywords)}):")
        seen_titles = set()
        rank = 1
        for title, sim, bonus in recommendations:
            if title in seen_titles:
                continue
            seen_titles.add(title)

            matched_song = next((s for s in music_data if s.get("title") == title), None)
            if not matched_song:
                continue
            artist = matched_song.get("artist", "알 수 없음")

            msg = f"{rank}. {title} - {artist} (유사도: {sim:.4f})"
            if bonus > 0:
                msg += f"제목 유사도 보너스 +{bonus:.3f} 적용됨"
            print(msg)

            rank += 1
            if rank > 10:
                break
