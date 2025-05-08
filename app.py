from flask import Flask, request, jsonify
from flask_cors import CORS
from bumper_pool_odds import calculate_odds
import logging

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@app.route("/predict", methods=["GET"])
def predict():
    player_a_id = request.args.get("player_a")
    player_b_id = request.args.get("player_b")

    if not player_a_id or not player_b_id:
        logger.warning("Missing player IDs in request")
        return jsonify({"error": "Missing player IDs"}), 400

    try:
        odds = calculate_odds(player_a_id, player_b_id)
        if not odds:
            logger.info(f"No match data available for players {player_a_id} vs {player_b_id}")
            return jsonify({"error": "No match data available"}), 404
        logger.info(f"Odds calculated for players {player_a_id} vs {player_b_id}")
        return jsonify(odds)
    except Exception as e:
        logger.error(f"Error calculating odds for players {player_a_id} vs {player_b_id}: {e}")
        return jsonify({"error": "Failed to calculate odds"}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
