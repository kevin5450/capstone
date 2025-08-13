from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

from content_filtering import (
    prepare_song_vectors,
    compute_user_avg_vector,
    recommend_top_n_songs
)

from collaborative_filtering import (
    load_user_item_matrix,
    recommend_user_cf
)

from hybrid_filtering import recommend_hybrid_weighted

from theme_based_filtering_ver3 import (
    load_music_data,
    train_word2vec,
    extract_keywords_simple,
    recommend_by_query_words
)

app = Flask(__name__)
CORS(app)

# 1. 콘텐츠 기반
@app.route("/recommend/content", methods=["GET"])
def recommend_content():
    user = request.args.get("user")
    if not user:
        return jsonify({"error": "사용자 이름이 없습니다."}), 400
    try:
        _, _, song_vectors, music_data = prepare_song_vectors()
        user_vector, liked_titles = compute_user_avg_vector(user, song_vectors)
        basic_results = recommend_top_n_songs(user_vector, song_vectors, music_data, liked_titles)

        recommendations = recommend_top_n_songs(user_vector, song_vectors, music_data, liked_titles)
        return jsonify({"user": user, "recommendations": recommendations})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 2. 협업 필터링
@app.route("/recommend/collab", methods=["GET"])
def recommend_collab():
    user = request.args.get("user")
    if not user:
        return jsonify({"error": "사용자 이름이 없습니다."}), 400
    try:
        uri = "mongodb://localhost:27017/"
        client = MongoClient(uri)
        music_data = list(client["music"]["music"].find({}, {"_id": 0}))
        user_ids, all_titles, matrix, user_likes = load_user_item_matrix(uri)

        recommendations = recommend_user_cf(user, user_ids, all_titles, matrix, user_likes, music_data)

        return jsonify({"user": user, "recommendations": recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# 3. 테마 기반 (자연어 문장 기반)
@app.route("/recommend/theme", methods=["GET"])
def recommend_theme():
    query = request.args.get("query")
    if not query:
        return jsonify({"error": "자연어 문장이 없습니다."}), 400
    try:
        uri = "mongodb://localhost:27017/"
        theme_music_data = load_music_data(uri, "music", "music")
        theme_model = train_word2vec(theme_music_data)

        keywords = extract_keywords_simple(query)
        if not keywords:
            return jsonify({"error": "유효한 키워드가 없습니다."}), 400

        results = recommend_by_query_words(keywords, theme_music_data, theme_model, top_n=10)

        recommendations = []
        seen = set()
        for title, sim in results:
            if title in seen:
                continue
            seen.add(title)
            song = next((s for s in theme_music_data if s.get("title") == title), None)
            if song:
                recommendations.append({
                    "title": song["title"],
                    "artist": song.get("artist", "unknown"),
                    "duration": song.get("duration", "--"),
                    "youtube_url": song.get("youtube_url", "")
                })
            if len(recommendations) >= 10:
                break

        return jsonify({"query": query, "recommendations": recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 4. 하이브리드 추천 (Weighted Score)
@app.route("/recommend/hybrid", methods=["GET"])
def hybrid_recommendation():
    user = request.args.get("user")
    if not user:
        return jsonify({"error": "사용자 이름이 없습니다."}), 400
    try:
        recommendations = recommend_hybrid_weighted(user)
        return jsonify({
            "user": user,
            "recommendations": recommendations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
