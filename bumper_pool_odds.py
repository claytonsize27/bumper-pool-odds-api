import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def fetch_match_data(player_a, player_b):
    # Fetch only necessary fields for performance optimization
    response = supabase.table("matches").select("winner_id, final_score").filter("is_finalized", "eq", True).filter(
        "or",
        f"(player_a_id.eq.{player_a},player_b_id.eq.{player_b})"
    ).execute()
    response = supabase.table("matches").select("*") \
        .filter("is_finalized", "eq", True) \
        .filter("player_a_id", "in", f"({player_a},{player_b})") \
        .filter("player_b_id", "in", f"({player_a},{player_b})") \
        .execute()

    if response.error:
        print(f"Error fetching matches: {response.error}")
        return []

    return response.data

def fetch_player_names():
    response = supabase.table("players").select("id, name").execute()
    if response.error:
        print(f"Error fetching players: {response.error}")
        return {}
    return {player["id"]: player["name"] for player in response.data}

def implied_odds(p):
    if p == 0: return "+∞"
    if p == 1: return "-∞"
    if p > 0.5:
        return f"-{int(100 * p / (1 - p))}"
    else:
        return f"+{int(100 * (1 - p) / p)}"

def calculate_odds(player_a_id, player_b_id):
    # Fetch matches and player names
    matches = fetch_match_data(player_a_id, player_b_id)
    player_names = fetch_player_names()

    player_a_name = player_names.get(player_a_id, "Unknown")
    player_b_name = player_names.get(player_b_id, "Unknown")

    player_a_wins = 0
    player_b_wins = 0
    player_a_margins = []
    player_b_margins = []

    # Track game margins and wins
    for match in matches:
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

    # Improved MOV calculations
    avg_mov_a = sum(player_a_margins) / len(player_a_margins) if player_a_margins else 1.5
    avg_mov_b = sum(player_b_margins) / len(player_b_margins) if player_b_margins else 1.5

    # Calculate weighted score margin probabilities
    margin_probs = {f"{i} ball": 0 for i in range(1, 6)}
    for i in range(1, 6):
        margin_probs[f"{i} ball"] = (
            (player_a_margins.count(i) / len(player_a_margins) if player_a_margins else 0) * player_a_win_rate +
            (player_b_margins.count(i) / len(player_b_margins) if player_b_margins else 0) * player_b_win_rate
        )

    # Calculate sweep odds more accurately
    sweep_odds_a = player_a_wins / total_games if player_a_wins > 0 else 0
    sweep_odds_b = player_b_wins / total_games if player_b_wins > 0 else 0

    # Build the final odds response
    odds = {
        "winner": player_a_name,
        "loser": player_b_name,
        "win_probabilities": {
            player_a_name: player_a_win_rate,
            player_b_name: player_b_win_rate,
        },
        "moneyline_odds": {
            player_a_name: implied_odds(player_a_win_rate),
            player_b_name: implied_odds(player_b_win_rate),
        },
        "spread_line": round(avg_mov_a - avg_mov_b, 1),
        "spread_odds": {
            player_a_name: implied_odds(player_a_win_rate),
            player_b_name: implied_odds(player_b_win_rate),
        },
        "sweep_odds": {
            player_a_name: implied_odds(sweep_odds_a ** 5),
            player_b_name: implied_odds(sweep_odds_b ** 5),
        },
        "score_margin_probs": margin_probs,
        "predicted_margin": round(avg_mov_a - avg_mov_b, 1)
    }

    return odds
    matches = fetch_match_data(player_a_id, player_b_id)
    player_names = fetch_player_names()

    player_a_name = player_names.get(player_a_id, "Unknown")
    player_b_name = player_names.get(player_b_id, "Unknown")

    player_a_wins = 0
    player_b_wins = 0
    player_a_margins = []
    player_b_margins = []

    for match in matches:
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

    total_games = player_a_wins + player_b_wins
    if total_games == 0:
        return {}

    player_a_win_rate = player_a_wins / total_games
    player_b_win_rate = player_b_wins / total_games

    avg_mov_a = sum(player_a_margins) / len(player_a_margins) if player_a_margins else 1.5
    avg_mov_b = sum(player_b_margins) / len(player_b_margins) if player_b_margins else 1.5

    spread_line = round((avg_mov_a - avg_mov_b) / 2, 1)
    spread_line_text = f"+{spread_line}" if spread_line > 0 else str(spread_line)

    margin_probs = {f"{i} ball": 0 for i in range(1, 6)}
    for i in range(1, 6):
        margin_probs[f"{i} ball"] = (
            (player_a_margins.count(i) / len(player_a_margins) if player_a_margins else 0) * player_a_win_rate +
            (player_b_margins.count(i) / len(player_b_margins) if player_b_margins else 0) * player_b_win_rate
        )

    odds = {
        "winner": player_a_name,
        "loser": player_b_name,
        "win_probabilities": {
            player_a_name: player_a_win_rate,
            player_b_name: player_b_win_rate,
        },
        "moneyline_odds": {
            player_a_name: implied_odds(player_a_win_rate),
            player_b_name: implied_odds(player_b_win_rate),
        },
        "spread_line": spread_line_text,
        "spread_odds": {
            player_a_name: implied_odds(player_a_win_rate),
            player_b_name: implied_odds(player_b_win_rate),
        },
        "sweep_odds": {
            player_a_name: implied_odds(player_a_win_rate ** 5),
            player_b_name: implied_odds(player_b_win_rate ** 5),
        },
        "score_margin_probs": margin_probs,
        "predicted_margin": round(avg_mov_a - avg_mov_b, 1)
    }

    return odds
