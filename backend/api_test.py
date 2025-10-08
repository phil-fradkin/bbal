import requests
import json

# Test the API
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
    data = response.json()
    if data:
        top_player = data[0]
        print(f"Top player: {top_player.get('name', 'Unknown')}")
        print(f"  Value: ${top_player.get('auction_value', 0)}")
        print(f"  Z-score: {top_player.get('z_score_total', 0):.2f}")
        print(f"  ADP rank: {top_player.get('adp_rank', 'N/A')}")
else:
    print(f"Error: {response.status_code}")
    print(response.text[:500])