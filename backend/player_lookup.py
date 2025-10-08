import requests
import json
import sys

# Get player name from command line argument (default to Jalen Johnson)
search_name = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'Jalen Johnson'

# Get all players
response = requests.post(
    'http://localhost:8000/calculate',
    json={
        'season': '2025',
        'min_games': 20,
        'league_teams': 12,
        'budget': 200
    }
)

if response.status_code == 200:
    players = response.json()

    # Find player by name (case insensitive)
    found_player = None
    search_parts = search_name.lower().split()

    for player in players:
        player_name = player.get('name', '').lower()
        if all(part in player_name for part in search_parts):
            found_player = player
            break

    if found_player:
        print(f"Player: {found_player['name']}")
        print(f"  Value: ${found_player.get('auction_value', 0)}")
        print(f"  Z-score: {found_player.get('z_score_total', 0):.2f}")
        print(f"  ADP rank: {found_player.get('adp_rank', 'N/A')}")
        print(f"  Value rank: {found_player.get('value_rank', 'N/A')}")
        print(f"\nStats:")
        print(f"  Games: {found_player.get('games', 0)}")
        print(f"  Points: {found_player.get('points', 0):.1f}")
        print(f"  Rebounds: {found_player.get('rebounds', 0):.1f}")
        print(f"  Assists: {found_player.get('assists', 0):.1f}")
        print(f"  Steals: {found_player.get('steals', 0):.1f}")
        print(f"  Blocks: {found_player.get('blocks', 0):.1f}")
        print(f"  3PM: {found_player.get('threes', 0):.1f}")
        print(f"  FG%: {found_player.get('fg_pct', 0):.3f}")
        print(f"  FT%: {found_player.get('ft_pct', 0):.3f}")
        print(f"  Turnovers: {found_player.get('turnovers', 0):.1f}")
        print(f"\nCategory Z-scores:")
        print(f"  Points Z: {found_player.get('z_points', 0):.2f}")
        print(f"  Rebounds Z: {found_player.get('z_rebounds', 0):.2f}")
        print(f"  Assists Z: {found_player.get('z_assists', 0):.2f}")
        print(f"  Steals Z: {found_player.get('z_steals', 0):.2f}")
        print(f"  Blocks Z: {found_player.get('z_blocks', 0):.2f}")
        print(f"  3PM Z: {found_player.get('z_threes', 0):.2f}")
        print(f"  FG% Z: {found_player.get('z_fg_pct', 0):.2f}")
        print(f"  FT% Z: {found_player.get('z_ft_pct', 0):.2f}")
        print(f"  TO Z: {found_player.get('z_turnovers', 0):.2f}")
    else:
        print(f"Player '{search_name}' not found")

    # Also check top 10 for comparison
    print("\n\nTop 10 players by value:")
    for i, p in enumerate(players[:10]):
        print(f"{i+1}. {p['name']:20} ${p['auction_value']:3} (z: {p['z_score_total']:5.2f}, ADP: {p.get('adp_rank', 'N/A')})")
else:
    print(f"Error: {response.status_code}")