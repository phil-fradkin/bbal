# NBA Fantasy Draft Tool

A comprehensive web application for NBA fantasy basketball auction drafts that combines real-time player statistics, Average Draft Position (ADP) data from FantasyPros, and advanced z-score analysis to calculate optimal player values with market-aware pricing.

## Features

- **Real NBA Stats**: Scrapes current season data from Basketball Reference
- **ADP Integration**: Fetches real-time Average Draft Position data from FantasyPros (262+ players)
- **Hybrid Valuation**: Blends market consensus (ADP) with statistical z-score analysis
- **Category Weighting**: Customize importance of each category (0.0-2.0x multipliers instead of binary punt)
- **Z-Score Analysis**: 9-category analysis with Value Above Replacement (VAR) calculations
- **Draft Tracking**: Track your team and opponents with actual bid prices
- **Visual Feedback**: Color-coded stats based on z-score strength (elite/good/poor)
- **Blended Rankings**: Smart combination of ADP and calculated rankings
- **Export Options**: CSV/JSON export for offline analysis
- **Market Inflation**: Adjustable rate for keeper leagues (0-100%)

## Quickstart for Coding Agents

### Prerequisites
```bash
# Required:
- Python 3.10+
- Node.js 18+
- npm or yarn
```

### Project Structure
```
nba_draft/
├── backend/
│   ├── main.py           # FastAPI server with CORS, endpoints: /calculate, /export/*
│   ├── scraper.py         # Basketball Reference + FantasyPros ADP scraper
│   ├── calculator.py      # Z-score, VAR, and hybrid auction value calculations
│   ├── requirements.txt   # Python deps: fastapi, pandas, beautifulsoup4, aiohttp
│   └── cache/            # Cached NBA stats (1 hour TTL)
├── frontend/
│   ├── src/
│   │   ├── App.tsx       # Main component with draft logic & category weights
│   │   ├── components/
│   │   │   ├── PlayerTable.tsx  # Sortable table with draft actions
│   │   │   ├── ZScoreCell.tsx   # Color-coded z-score display
│   │   │   └── StatCell.tsx     # Color-coded stat display
│   │   └── types/
│   │       └── Player.ts # TypeScript interface with all stats + ADP
│   ├── package.json      # Node deps: react, axios, vite
│   └── vite.config.ts    # Dev proxy: /api → localhost:8000
└── start.sh              # Launches both servers in parallel
```

### Quick Installation

```bash
# Clone and setup
git clone <repo-url>
cd nba_draft

# Option 1: Use the start script (recommended)
chmod +x start.sh
./start.sh

# Option 2: Manual setup
# Terminal 1 - Backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev

# Access at http://localhost:3000
```

## Key API Endpoints

### Calculate Player Values
```bash
POST http://localhost:8000/calculate
Content-Type: application/json

{
  "season": "2025",
  "min_games": 20,
  "category_weights": {
    "points": 1.0,
    "rebounds": 1.0,
    "assists": 1.0,
    "steals": 1.5,      # Boost steals importance
    "blocks": 1.5,      # Boost blocks importance
    "threes": 1.0,
    "fg_pct": 0.5,      # De-emphasize FG%
    "ft_pct": 1.0,
    "turnovers": 0.0    # Punt turnovers completely
  },
  "inflation_rate": 0.0,
  "league_teams": 12,
  "roster_size": 13,
  "budget": 200
}
```

### Response Format
```json
{
  "name": "Nikola Jokić",
  "team": "DEN",
  "position": "C",
  "games": 70,
  "points": 29.6,
  "rebounds": 12.7,
  "assists": 10.2,
  "auction_value": 56,      # Blended ADP + z-score value
  "z_score_total": 14.93,
  "adp": 1.0,               # FantasyPros ADP
  "adp_rank": 1,
  "blend_rank": 1,          # Weighted combo of ADP + value
  "value_rank": 1,
  "z_points": 2.15,         # Individual category z-scores
  "z_rebounds": 2.89,
  "z_assists": 3.45,
  ...
}
```

## Core Algorithms

### Z-Score Calculation
```python
# backend/calculator.py
z_score = (player_value - mean) / std_dev
weighted_z = z_score * category_weight  # 0.0 to 2.0
total_z = sum(weighted_z_scores)
```

### Value Above Replacement (VAR)
```python
# Simple replacement level: player at position 156 (12 teams × 13 roster)
replacement_level = z_score_at_position(156)
VAR = player_z_score - replacement_level
auction_value = (VAR × dollars_per_VAR) + $1
```

### Hybrid Valuation (NEW!)
```python
# backend/calculator.py::_blend_values()
if adp_rank <= 20:
    weight = 0.7  # 70% ADP, 30% z-score
elif adp_rank <= 50:
    weight = 0.6  # 60% ADP, 40% z-score
elif adp_rank <= 100:
    weight = 0.5  # 50/50 split
else:
    weight = 0.3  # 30% ADP, 70% z-score

final_value = (adp_value * weight) + (z_score_value * (1 - weight))
```

## Important Files for Modifications

### Add New Stat Category
1. `backend/calculator.py`: Add to `self.categories` list
2. `frontend/src/types/Player.ts`: Add to Player interface
3. `frontend/src/components/PlayerTable.tsx`: Add table column

### Adjust Valuation Logic
- `backend/calculator.py::_blend_values()`: Modify ADP/z-score weights
- `backend/calculator.py::_calculate_adp_based_values()`: Adjust $ curve

### Change Data Sources
- `backend/scraper.py::_scrape_basketball_reference()`: NBA stats
- `backend/scraper.py::_fetch_adp_data()`: FantasyPros ADP

### UI Customization
- `frontend/src/index.css`: All styling and colors
- `frontend/src/components/PlayerTable.tsx`: Table logic
- `frontend/src/App.tsx`: Controls and weights

## Common Tasks for Agents

### Clear Cache (Force Fresh Data)
```bash
rm backend/cache/*.json
```

### Test Specific Configuration
```python
# Quick test
curl -X POST http://localhost:8000/calculate \
  -H "Content-Type: application/json" \
  -d '{"season": "2025", "min_games": 20, "category_weights": {"blocks": 2.0}}'
```

### Add New Data Source
1. Create scraper method in `scraper.py`
2. Merge in `_merge_adp_data()` style
3. Add to Player type in `frontend/src/types/Player.ts`

### Deploy to Production
```bash
# Backend to Railway
cd backend
railway up

# Frontend to Vercel
cd frontend
echo "REACT_APP_API_URL=https://your-backend.railway.app" > .env.production
vercel --prod
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Failed to calculate values" | Clear cache: `rm backend/cache/*.json` |
| ADP not updating | FantasyPros HTML changed, check `_fetch_adp_data()` |
| Wrong values | Check replacement level (~0-1 z-score expected) |
| Duplicate players | Basketball Reference trade handling in `_scrape_basketball_reference()` |

## Environment Variables

```bash
# backend/.env
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

# frontend/.env.production
REACT_APP_API_URL=https://your-backend.railway.app
```

## Contributors
- Marto Skreto
