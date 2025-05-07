from flask import Flask, request, jsonify
from bumper_pool_odds import calculate_odds

app = Flask(__name__)

@app.route("/predict", methods=["GET"])
def predict():
    player_a_id = request.args.get("player_a")
    player_b_id = request.args.get("player_b")

    if not player_a_id or not player_b_id:
        return jsonify({"error": "Missing player IDs"}), 400

    odds = calculate_odds(player_a_id, player_b_id)
    return jsonify(odds)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
