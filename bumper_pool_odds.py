import os
import numpy as np
from scipy.stats import norm
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def prob_to_american(p):
    if p == 0:
        return "+∞"
    elif p == 1:
        return "-∞"
    elif p > 0.99:
        return "-10000"
    elif p < 0.01:
        return "+10000"
    elif p > 0.5:
        return f"-{int(100 * p / (1 - p))}"
    else:
        return f"+{int(100 * (1 - p) / p)}"

def calculate_margin_and_std(margins):
    if not margins:
        return 0, 1.5  # Default to 1.5 if no data is available
    mean = np.mean(margins)
    std = np.std(margins) if len(margins) > 1 else 1.5
    return mean, std

def calculate_sweep_odds(mu, sigma):
    # Probability of winning by exactly 5-0 (5 or more)
    return 1 - norm.cdf(5, mu, sigma)

def calculate_exact_margin_probs(mu, sigma):
    # Probability of winning by each margin from 1 to 5 balls
    margin_probs = {}
    for i in range(1, 6):
        prob_win = norm.cdf(i + 0.5, mu, sigma) - norm.cdf(i - 0.5, mu, sigma)
        prob_loss = norm.cdf(-i + 0.5, mu, sigma) - norm.cdf(-i - 0.5, mu, sigma)
        margin_probs[f"{i} ball"] = prob_win
        margin_probs[f"-{i} ball"] = prob_loss
    return margin_probs

def fetch_player_names():
    try:
        response = supabase.table("players").select("id, name").execute()
        if not response.data:
            logger.error(f"No player data returned: {response}")
            return {}
        return {player["id"]: player["name"] for player in response.data}
    except Exception as e:
        logger.error(f"Failed to fetch player names: {e}", exc_info=True)
        return {}

def calculate_odds(player_a_id, player_b_id):
    try:
        # Fetch player names for UUID conversion
        player_names = fetch_player_names()

        # Fetch match data
        response = supabase.table("matches").select("winner_id, final_score, player_a_id, player_b_id").filter("is_finalized", "eq", True).filter(
            "or",
            f"(player_a_id.eq.{player_a_id},player_b_id.eq.{player_b_id})",
            f"(player_a_id.eq.{player_b_id},player_b_id.eq.{player_a_id})"
        ).execute()

        if not response.data:
            logger.error(f"No match data returned: {response}")
            return {}

        # Calculate historical margins and head-to-head records
        player_a_margins = []
        player_b_margins = []
        player_a_wins = 0
        player_b_wins = 0

        for match in response.data:
            winner_id = match["winner_id"]
            final_score = match.get("final_score", "")

            if winner_id == player_a_id:
                player_a_wins += 1
                if final_score:
                    margin = int(final_score.split('-')[0])
                    player_a_margins.append(margin)
            elif winner_id == player_b_id:
                player_b_wins += 1
                if final_score:
                    margin = int(final_score.split('-')[0])
                    player_b_margins.append(margin)

        # Calculate basic win rates
        total_games = player_a_wins + player_b_wins
        if total_games == 0:
            return {}

        player_a_win_rate = player_a_wins / total_games
        player_b_win_rate = player_b_wins / total_games

        # Calculate margin and standard deviation
        mean_a, std_a = calculate_margin_and_std(player_a_margins)
        mean_b, std_b = calculate_margin_and_std(player_b_margins)
        predicted_margin = mean_a - mean_b
        mu = predicted_margin if player_a_win_rate > player_b_win_rate else -predicted_margin
        sigma = (std_a + std_b) / 2

        # Convert player IDs to names
        player_a_name = player_names.get(player_a_id, player_a_id)
        player_b_name = player_names.get(player_b_id, player_b_id)

        # Build the final odds response
        odds = {
            "winner": player_a_name if player_a_win_rate > player_b_win_rate else player_b_name,
            "loser": player_b_name if player_a_win_rate > player_b_win_rate else player_a_name,
            "win_probabilities": {
                player_a_name: player_a_win_rate,
                player_b_name: player_b_win_rate,
            },
            "moneyline_odds": {
                player_a_name: prob_to_american(player_a_win_rate),
                player_b_name: prob_to_american(player_b_win_rate),
            },
            "spread_line": round(mu, 1),
            "spread_odds": {
                player_a_name: prob_to_american(norm.cdf(mu / sigma)),
                player_b_name: prob_to_american(1 - norm.cdf(mu / sigma)),
            },
            "sweep_odds": {
                player_a_name: prob_to_american(calculate_sweep_odds(mu, sigma)),
                player_b_name: prob_to_american(calculate_sweep_odds(-mu, sigma)),
            },
            "score_margin_probs": calculate_exact_margin_probs(mu, sigma),
            "predicted_margin": round(mu, 1)
        }

        return odds
    except Exception as e:
        logger.error(f"Failed to calculate odds: {e}", exc_info=True)
        return {}
