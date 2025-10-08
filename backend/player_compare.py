import requests
import json

response = requests.post(
    'http://localhost:8000/calculate',
    json={'season': '2025', 'min_games': 20, 'league_teams': 12, 'budget': 200}
)

if response.status_code == 200:
    players = response.json()

    # Find players with similar points (19-21 PPG)
    similar = [p for p in players if 19 <= p.get('points', 0) <= 21]
    similar = sorted(similar, key=lambda x: x['auction_value'], reverse=True)[:10]

    print('Players with 19-21 PPG:')
    print('Name                      Value  Z-Score  PTS   REB   AST   STL   BLK   3PM   FG%    FT%    TO')
    print('-' * 105)
    for p in similar:
        print(f"{p['name']:25} ${p['auction_value']:3}   {p['z_score_total']:6.2f}  {p['points']:4.1f}  {p['rebounds']:4.1f}  {p['assists']:4.1f}  {p['steals']:4.1f}  {p['blocks']:4.1f}  {p['threes']:4.1f}  {p['fg_pct']:.3f}  {p['ft_pct']:.3f}  {p['turnovers']:4.1f}")