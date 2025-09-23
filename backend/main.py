from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import json
import io
import csv
from datetime import datetime

from scraper import NBADataScraper
from calculator import AuctionValueCalculator

app = FastAPI(title="NBA Auction Value Calculator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scraper = NBADataScraper()
calculator = AuctionValueCalculator()

class CalculateRequest(BaseModel):
    season: Optional[str] = "2025"
    min_games: Optional[int] = 20
    punted_cats: Optional[List[str]] = []  # Keep for backward compatibility
    category_weights: Optional[Dict[str, float]] = {}  # New weight system
    inflation_rate: Optional[float] = 0.0
    league_teams: Optional[int] = 12
    roster_size: Optional[int] = 13
    budget: Optional[int] = 200

@app.get("/")
def read_root():
    return {
        "name": "NBA Auction Value Calculator API",
        "version": "1.0.0",
        "endpoints": [
            "/players",
            "/calculate",
            "/export/csv",
            "/export/json"
        ]
    }

@app.get("/players")
async def get_players(
    season: Optional[str] = "2025",
    min_games: Optional[int] = 20
):
    try:
        players = await scraper.get_player_stats(season, min_games)
        return players
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/calculate")
async def calculate_values(request: CalculateRequest):
    try:
        players = await scraper.get_player_stats(request.season, request.min_games)

        values = calculator.calculate_auction_values(
            players,
            punted_cats=request.punted_cats,
            category_weights=request.category_weights,
            inflation_rate=request.inflation_rate,
            league_teams=request.league_teams,
            roster_size=request.roster_size,
            budget=request.budget
        )

        return values
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/csv")
async def export_csv(
    data: List[Dict[str, Any]]
):
    try:
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=nba_auction_values_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/json")
async def export_json(
    data: List[Dict[str, Any]]
):
    try:
        json_str = json.dumps(data, indent=2)
        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=nba_auction_values_{datetime.now().strftime('%Y%m%d')}.json"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)