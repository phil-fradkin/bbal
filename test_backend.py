#!/usr/bin/env python3
"""
Test script for NBA Auction Value Calculator backend
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_api():
    print("Testing NBA Auction Value Calculator API...")
    print("-" * 50)

    # Test 1: Root endpoint
    try:
        response = requests.get(f"{BASE_URL}/")
        assert response.status_code == 200
        print("✓ Root endpoint working")
    except Exception as e:
        print(f"✗ Root endpoint failed: {e}")
        return False

    # Test 2: Calculate values with default settings
    try:
        payload = {
            "season": "2025",
            "min_games": 20,
            "punted_cats": [],
            "inflation_rate": 0,
            "league_teams": 12,
            "roster_size": 13,
            "budget": 200
        }

        print("\nCalculating player values...")
        response = requests.post(f"{BASE_URL}/calculate", json=payload)
        assert response.status_code == 200

        players = response.json()
        print(f"✓ Calculated values for {len(players)} players")

        # Show top 10 players
        if players:
            print("\nTop 10 Players by Value:")
            print("-" * 50)
            print(f"{'Rank':<5} {'Name':<25} {'Team':<5} {'Value':<8}")
            print("-" * 50)

            for i, player in enumerate(players[:10], 1):
                name = player.get('name', 'Unknown')[:24]
                team = player.get('team', 'N/A')
                value = player.get('auction_value', 0)
                print(f"{i:<5} {name:<25} {team:<5} ${value:<7}")

    except Exception as e:
        print(f"✗ Calculate endpoint failed: {e}")
        return False

    # Test 3: Calculate with punt strategy
    try:
        payload["punted_cats"] = ["turnovers", "ft_pct"]
        payload["inflation_rate"] = 15

        print("\n\nTesting punt strategy (punting TO + FT%)...")
        response = requests.post(f"{BASE_URL}/calculate", json=payload)
        assert response.status_code == 200

        punt_players = response.json()
        print(f"✓ Calculated punt values for {len(punt_players)} players")

        # Show top 5 with punt
        if punt_players:
            print("\nTop 5 Players (Punting TO + FT%, 15% inflation):")
            print("-" * 50)
            for i, player in enumerate(punt_players[:5], 1):
                name = player.get('name', 'Unknown')[:24]
                value = player.get('auction_value', 0)
                print(f"{i}. {name}: ${value}")

    except Exception as e:
        print(f"✗ Punt strategy test failed: {e}")
        return False

    print("\n" + "=" * 50)
    print("All tests passed! ✓")
    print("=" * 50)
    return True

if __name__ == "__main__":
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
    except requests.exceptions.ConnectionError:
        print("ERROR: Backend server is not running!")
        print("Please start the backend server first:")
        print("  cd backend")
        print("  python main.py")
        sys.exit(1)

    # Run tests
    success = test_api()
    sys.exit(0 if success else 1)