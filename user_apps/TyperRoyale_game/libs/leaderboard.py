"""Leaderboard management for TyperRoyale"""

import json

# Leaderboard keys for different modes and difficulties
def get_leaderboard_key(mode, difficulty):
    """Get config key for specific leaderboard"""
    return f"typer_lb_{mode}_{difficulty}"

def get_leaderboard(badge, mode, difficulty):
    """
    Get leaderboard for mode/difficulty

    Returns list of dicts: [{"name": "ABC", "score": 450, "metric": "45.2s"}, ...]
    """
    key = get_leaderboard_key(mode, difficulty)
    data = badge.config.get(key)

    if not data:
        return []

    try:
        return json.loads(data.decode())
    except:
        return []

def save_leaderboard(badge, mode, difficulty, leaderboard):
    """Save leaderboard to config"""
    key = get_leaderboard_key(mode, difficulty)
    data = json.dumps(leaderboard)
    badge.config.set(key, data.encode())
    badge.config.flush()

def add_score(badge, mode, difficulty, name, score, metric):
    """
    Add a score to the leaderboard

    Args:
        badge: Badge object
        mode: Game mode (score, time, survival)
        difficulty: Difficulty level
        name: Player name (3 chars)
        score: Numeric score for ranking
        metric: Display string (e.g., "450 pts", "32.5s", "15 words")

    Returns:
        (rank, total) - Player's rank (1-5) and total entries, or (None, total) if not in top 5
    """
    leaderboard = get_leaderboard(badge, mode, difficulty)

    # Add new entry
    new_entry = {
        "name": name,
        "score": score,
        "metric": metric
    }
    leaderboard.append(new_entry)

    # Sort based on mode
    if mode == "time":
        # Time trial: lower is better
        leaderboard.sort(key=lambda x: x["score"])
    else:
        # Score/Survival: higher is better
        leaderboard.sort(key=lambda x: x["score"], reverse=True)

    # Keep only top 5
    leaderboard = leaderboard[:5]

    # Find player's rank
    rank = None
    for i, entry in enumerate(leaderboard):
        if entry["name"] == name and entry["score"] == score and entry["metric"] == metric:
            rank = i + 1
            break

    # Save updated leaderboard
    save_leaderboard(badge, mode, difficulty, leaderboard)

    return (rank, len(leaderboard))

def qualifies_for_leaderboard(badge, mode, difficulty, score):
    """Check if score qualifies for top 5"""
    leaderboard = get_leaderboard(badge, mode, difficulty)

    if len(leaderboard) < 5:
        return True

    if mode == "time":
        # Time trial: lower is better
        worst_score = max(entry["score"] for entry in leaderboard)
        return score < worst_score
    else:
        # Score/Survival: higher is better
        worst_score = min(entry["score"] for entry in leaderboard)
        return score > worst_score
