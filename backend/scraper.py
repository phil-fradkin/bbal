import asyncio
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import httpx
import aiohttp
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
import os
import logging
from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, leagueleaders

logger = logging.getLogger(__name__)

class NBADataScraper:
    def __init__(self):
        self.cache_dir = "cache"
        self.cache_duration = timedelta(hours=1)
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    async def get_player_stats(self, season: str = "2025", min_games: int = 10) -> List[Dict]:
        # Ensure cache directory exists
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        cache_file = os.path.join(self.cache_dir, f"nba_stats_{season}_{min_games}.json")

        if self._is_cache_valid(cache_file):
            with open(cache_file, 'r') as f:
                return json.load(f)

        try:
            # For testing, we'll use sample data first
            # In production, uncomment the line below
            data = await self._scrape_basketball_reference(season, min_games)
            # data = self._load_sample_data()
        except Exception as e:
            print(f"Basketball Reference scraping failed: {e}")
            try:
                data = self._fetch_from_nba_api(season, min_games)
            except Exception as e2:
                print(f"NBA API fetch failed: {e2}")
                data = self._load_sample_data()

        # Fetch and merge ADP data
        try:
            adp_data = await self._fetch_adp_data()
            data = self._merge_adp_data(data, adp_data)
        except Exception as e:
            print(f"ADP fetch failed: {e}")
            # Add default ADP values if fetch fails
            for i, player in enumerate(data):
                player['adp'] = None
                player['adp_rank'] = None

        with open(cache_file, 'w') as f:
            json.dump(data, f)

        return data

    async def _scrape_basketball_reference(self, season: str, min_games: int) -> List[Dict]:
        url = f"https://www.basketball-reference.com/leagues/NBA_{season}_per_game.html"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')
        table = soup.find('table', {'id': 'per_game_stats'})

        if not table:
            raise ValueError("Could not find stats table")

        headers = []
        for th in table.find('thead').find_all('tr')[-1].find_all('th'):
            headers.append(th.get('data-stat', ''))

        rows = []
        tbody = table.find('tbody')
        if not tbody:
            return []

        all_trs = tbody.find_all('tr')

        for tr in all_trs[:5]:
            # Skip header rows that appear in tbody
            if tr.get('class') and 'thead' in ' '.join(tr.get('class', [])):
                continue

            row_data = {}
            for td in tr.find_all(['th', 'td']):
                stat = td.get('data-stat', '')
                value = td.text.strip()
                row_data[stat] = value

            # The player name field might be 'player' or 'name_display' depending on the page
            player_name = row_data.get('player') or row_data.get('name_display')
            if row_data and player_name:  # Make sure we have a player name
                row_data['player'] = player_name  # Normalize to 'player' key
                rows.append(row_data)

        # Process rest of rows without debug
        for tr in all_trs[5:]:
            if tr.get('class') and 'thead' in ' '.join(tr.get('class', [])):
                continue

            row_data = {}
            for td in tr.find_all(['th', 'td']):
                stat = td.get('data-stat', '')
                value = td.text.strip()
                row_data[stat] = value

            player_name = row_data.get('player') or row_data.get('name_display')
            if row_data and player_name:
                row_data['player'] = player_name
                rows.append(row_data)

        processed_data = []
        for row in rows:
            try:
                games = int(float(row.get('g') or row.get('games', '0') or '0'))
                if games < min_games:
                    continue

                player_data = {
                    'name': row.get('player', ''),
                    'team': row.get('team_id') or row.get('team_name_abbr', ''),
                    'position': row.get('pos', ''),
                    'games': games,
                    'minutes': float(row.get('mp_per_g', '0') or '0'),
                    'points': float(row.get('pts_per_g', '0') or '0'),
                    'rebounds': float(row.get('trb_per_g', '0') or '0'),
                    'assists': float(row.get('ast_per_g', '0') or '0'),
                    'steals': float(row.get('stl_per_g', '0') or '0'),
                    'blocks': float(row.get('blk_per_g', '0') or '0'),
                    'threes': float(row.get('fg3_per_g', '0') or '0'),
                    'fgm': float(row.get('fg_per_g', '0') or '0'),
                    'fga': float(row.get('fga_per_g', '0') or '0'),
                    'ftm': float(row.get('ft_per_g', '0') or '0'),
                    'fta': float(row.get('fta_per_g', '0') or '0'),
                    'turnovers': float(row.get('tov_per_g', '0') or '0'),
                    'fg_pct': float(row.get('fg_pct', '0') or '0'),
                    'ft_pct': float(row.get('ft_pct', '0') or '0')
                }

                player_data['total_points'] = player_data['points'] * player_data['games']
                player_data['total_rebounds'] = player_data['rebounds'] * player_data['games']
                player_data['total_assists'] = player_data['assists'] * player_data['games']
                player_data['total_steals'] = player_data['steals'] * player_data['games']
                player_data['total_blocks'] = player_data['blocks'] * player_data['games']
                player_data['total_threes'] = player_data['threes'] * player_data['games']
                player_data['total_fgm'] = player_data['fgm'] * player_data['games']
                player_data['total_fga'] = player_data['fga'] * player_data['games']
                player_data['total_ftm'] = player_data['ftm'] * player_data['games']
                player_data['total_fta'] = player_data['fta'] * player_data['games']
                player_data['total_turnovers'] = player_data['turnovers'] * player_data['games']

                processed_data.append(player_data)

            except (ValueError, TypeError) as e:
                print(f"Error processing row: {e}")
                continue

        # Deduplicate players - preferring TOT/2TM rows, or summing if needed
        deduplicated = {}
        for player in processed_data:
            name = player['name']
            team = player['team']

            if team in ['TOT', '2TM', '3TM', '4TM']:
                # This is the official total, always use it
                deduplicated[name] = player
            elif name not in deduplicated:
                # First time seeing this player
                deduplicated[name] = player
            elif deduplicated[name]['team'] not in ['TOT', '2TM', '3TM', '4TM']:
                # We already have this player but no total row exists
                # This means they were traded but no TOT row - shouldn't happen but handle it
                # Keep the one with more games
                if player['games'] > deduplicated[name]['games']:
                    deduplicated[name] = player

        return list(deduplicated.values())

    def _fetch_from_nba_api(self, season: str, min_games: int) -> List[Dict]:
        season_str = f"{int(season)-1}-{season[-2:]}"

        try:
            leaders = leagueleaders.LeagueLeaders(
                league_id='00',
                per_mode48='PerGame',
                season=season_str,
                season_type_all_star='Regular Season'
            )

            df = leaders.get_data_frames()[0]

            processed_data = []
            for _, row in df.iterrows():
                if row['GP'] < min_games:
                    continue

                player_data = {
                    'name': row['PLAYER'],
                    'team': row.get('TEAM', ''),
                    'position': row.get('PLAYER_POSITION', ''),
                    'games': int(row['GP']),
                    'minutes': float(row.get('MIN', 0)),
                    'points': float(row.get('PTS', 0)),
                    'rebounds': float(row.get('REB', 0)),
                    'assists': float(row.get('AST', 0)),
                    'steals': float(row.get('STL', 0)),
                    'blocks': float(row.get('BLK', 0)),
                    'threes': float(row.get('FG3M', 0)),
                    'fgm': float(row.get('FGM', 0)),
                    'fga': float(row.get('FGA', 0)),
                    'ftm': float(row.get('FTM', 0)),
                    'fta': float(row.get('FTA', 0)),
                    'turnovers': float(row.get('TOV', 0)),
                    'fg_pct': float(row.get('FG_PCT', 0)),
                    'ft_pct': float(row.get('FT_PCT', 0))
                }

                player_data['total_points'] = player_data['points'] * player_data['games']
                player_data['total_rebounds'] = player_data['rebounds'] * player_data['games']
                player_data['total_assists'] = player_data['assists'] * player_data['games']
                player_data['total_steals'] = player_data['steals'] * player_data['games']
                player_data['total_blocks'] = player_data['blocks'] * player_data['games']
                player_data['total_threes'] = player_data['threes'] * player_data['games']
                player_data['total_fgm'] = player_data['fgm'] * player_data['games']
                player_data['total_fga'] = player_data['fga'] * player_data['games']
                player_data['total_ftm'] = player_data['ftm'] * player_data['games']
                player_data['total_fta'] = player_data['fta'] * player_data['games']
                player_data['total_turnovers'] = player_data['turnovers'] * player_data['games']

                processed_data.append(player_data)

            return processed_data

        except Exception as e:
            print(f"NBA API error: {e}")
            raise

    def _load_sample_data(self) -> List[Dict]:
        sample_players = [
            {
                'name': 'Nikola Jokic', 'team': 'DEN', 'position': 'C', 'games': 79,
                'points': 26.4, 'rebounds': 12.4, 'assists': 9.0, 'steals': 1.4,
                'blocks': 0.9, 'threes': 1.0, 'fgm': 9.8, 'fga': 16.5,
                'ftm': 5.8, 'fta': 6.9, 'turnovers': 3.0, 'minutes': 34.6
            },
            {
                'name': 'Luka Doncic', 'team': 'DAL', 'position': 'PG', 'games': 70,
                'points': 33.9, 'rebounds': 9.2, 'assists': 9.8, 'steals': 1.4,
                'blocks': 0.5, 'threes': 3.4, 'fgm': 11.2, 'fga': 23.5,
                'ftm': 8.1, 'fta': 10.6, 'turnovers': 4.0, 'minutes': 37.5
            },
            {
                'name': 'Giannis Antetokounmpo', 'team': 'MIL', 'position': 'PF', 'games': 73,
                'points': 30.4, 'rebounds': 11.5, 'assists': 6.5, 'steals': 1.2,
                'blocks': 1.1, 'threes': 0.8, 'fgm': 11.6, 'fga': 19.2,
                'ftm': 6.5, 'fta': 9.6, 'turnovers': 3.4, 'minutes': 35.2
            },
            {
                'name': 'Joel Embiid', 'team': 'PHI', 'position': 'C', 'games': 39,
                'points': 34.7, 'rebounds': 11.0, 'assists': 5.6, 'steals': 1.2,
                'blocks': 1.7, 'threes': 1.3, 'fgm': 11.0, 'fga': 20.1,
                'ftm': 10.9, 'fta': 11.9, 'turnovers': 3.9, 'minutes': 33.6
            },
            {
                'name': 'Jayson Tatum', 'team': 'BOS', 'position': 'SF', 'games': 74,
                'points': 26.9, 'rebounds': 8.1, 'assists': 4.9, 'steals': 1.0,
                'blocks': 0.6, 'threes': 3.0, 'fgm': 9.3, 'fga': 20.2,
                'ftm': 5.3, 'fta': 6.1, 'turnovers': 2.5, 'minutes': 35.7
            },
            {
                'name': 'Stephen Curry', 'team': 'GSW', 'position': 'PG', 'games': 74,
                'points': 26.4, 'rebounds': 4.5, 'assists': 5.1, 'steals': 0.7,
                'blocks': 0.4, 'threes': 4.8, 'fgm': 9.0, 'fga': 19.1,
                'ftm': 3.6, 'fta': 4.0, 'turnovers': 2.8, 'minutes': 32.7
            },
            {
                'name': 'Damian Lillard', 'team': 'MIL', 'position': 'PG', 'games': 73,
                'points': 24.3, 'rebounds': 4.4, 'assists': 7.0, 'steals': 1.0,
                'blocks': 0.3, 'threes': 2.8, 'fgm': 7.6, 'fga': 17.5,
                'ftm': 6.3, 'fta': 6.9, 'turnovers': 2.2, 'minutes': 35.1
            },
            {
                'name': 'Anthony Davis', 'team': 'LAL', 'position': 'PF', 'games': 76,
                'points': 24.7, 'rebounds': 12.6, 'assists': 3.5, 'steals': 1.2,
                'blocks': 2.3, 'threes': 0.3, 'fgm': 10.0, 'fga': 17.8,
                'ftm': 4.4, 'fta': 5.7, 'turnovers': 2.1, 'minutes': 35.5
            },
            {
                'name': 'LeBron James', 'team': 'LAL', 'position': 'SF', 'games': 71,
                'points': 25.7, 'rebounds': 7.3, 'assists': 8.3, 'steals': 1.3,
                'blocks': 0.5, 'threes': 2.1, 'fgm': 9.5, 'fga': 17.3,
                'ftm': 4.6, 'fta': 6.1, 'turnovers': 3.5, 'minutes': 35.3
            },
            {
                'name': 'Karl-Anthony Towns', 'team': 'MIN', 'position': 'C', 'games': 62,
                'points': 21.8, 'rebounds': 8.3, 'assists': 3.0, 'steals': 0.7,
                'blocks': 0.7, 'threes': 2.4, 'fgm': 8.0, 'fga': 16.0,
                'ftm': 3.4, 'fta': 4.0, 'turnovers': 2.9, 'minutes': 32.9
            }
        ]

        for player in sample_players:
            for stat in ['points', 'rebounds', 'assists', 'steals', 'blocks',
                        'threes', 'fgm', 'fga', 'ftm', 'fta', 'turnovers']:
                player[f'total_{stat}'] = player[stat] * player['games']
            player['fg_pct'] = player['fgm'] / player['fga'] if player['fga'] > 0 else 0
            player['ft_pct'] = player['ftm'] / player['fta'] if player['fta'] > 0 else 0

        return sample_players

    async def _fetch_adp_data(self) -> Dict[str, Dict]:
        """Fetch ADP data from FantasyPros"""
        try:
            url = "https://www.fantasypros.com/nba/adp/overall.php"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch ADP data: {response.status}")
                        return self._get_fallback_adp()

                    html = await response.text()

            soup = BeautifulSoup(html, 'html.parser')

            # Find the ADP table
            table = soup.find('table', {'id': 'data'})
            if not table:
                # Try alternative table selectors
                table = soup.find('table', class_='table')

            if not table:
                logger.warning("Could not find ADP table")
                return self._get_fallback_adp()

            adp_data = {}

            # Parse table rows
            rows = table.find_all('tr')[1:]  # Skip header

            for idx, row in enumerate(rows, 1):
                cols = row.find_all('td')
                if len(cols) < 3:
                    continue

                try:
                    # Player name is usually in the 2nd column (index 1)
                    player_cell = cols[1]

                    # Extract player name - handle different HTML structures
                    player_name = None

                    # Try to find an anchor tag first
                    anchor = player_cell.find('a')
                    if anchor:
                        player_name = anchor.get_text(strip=True)
                    else:
                        # Fall back to direct text
                        player_name = player_cell.get_text(strip=True)

                    # Clean up the name (remove team/position info if present)
                    if player_name:
                        # Remove anything in parentheses
                        player_name = player_name.split('(')[0].strip()
                        # Remove position abbreviations at the end
                        for pos in [' PG', ' SG', ' SF', ' PF', ' C', ' G', ' F']:
                            if player_name.endswith(pos):
                                player_name = player_name[:-len(pos)]

                        # Get ADP value - usually in column 3 or 4
                        adp_value = None
                        for col_idx in [2, 3, 4]:
                            if col_idx < len(cols):
                                adp_text = cols[col_idx].get_text(strip=True)
                                try:
                                    adp_value = float(adp_text)
                                    break
                                except ValueError:
                                    continue

                        if adp_value:
                            normalized_name = self._normalize_name(player_name)
                            adp_data[normalized_name] = {
                                'adp': adp_value,
                                'adp_rank': idx
                            }
                            logger.info(f"Found ADP: {player_name} = {adp_value} (rank {idx})")

                except Exception as e:
                    logger.debug(f"Error parsing row {idx}: {e}")
                    continue

            if not adp_data:
                logger.warning("No ADP data parsed, using fallback")
                return self._get_fallback_adp()

            logger.info(f"Successfully parsed {len(adp_data)} players' ADP data")
            return adp_data

        except Exception as e:
            logger.error(f"Error fetching ADP data: {e}")
            return self._get_fallback_adp()

    def _get_fallback_adp(self) -> Dict[str, Dict]:
        """Return fallback ADP data if scraping fails"""
        # Mock ADP data - top players with realistic ADPs
        mock_adp = {
            'Nikola Jokic': {'adp': 1.2, 'adp_rank': 1},
            'Luka Doncic': {'adp': 2.5, 'adp_rank': 2},
            'Giannis Antetokounmpo': {'adp': 3.1, 'adp_rank': 3},
            'Jayson Tatum': {'adp': 4.8, 'adp_rank': 4},
            'Joel Embiid': {'adp': 5.3, 'adp_rank': 5},
            'Shai Gilgeous-Alexander': {'adp': 6.2, 'adp_rank': 6},
            'Stephen Curry': {'adp': 7.5, 'adp_rank': 7},
            'Tyrese Haliburton': {'adp': 8.1, 'adp_rank': 8},
            'Damian Lillard': {'adp': 9.7, 'adp_rank': 9},
            'Anthony Davis': {'adp': 10.4, 'adp_rank': 10},
            'LeBron James': {'adp': 11.8, 'adp_rank': 11},
            'Kevin Durant': {'adp': 12.3, 'adp_rank': 12},
            'Donovan Mitchell': {'adp': 13.6, 'adp_rank': 13},
            'Anthony Edwards': {'adp': 14.2, 'adp_rank': 14},
            'Jaylen Brown': {'adp': 15.9, 'adp_rank': 15},
            'Karl-Anthony Towns': {'adp': 16.7, 'adp_rank': 16},
            'Domantas Sabonis': {'adp': 17.4, 'adp_rank': 17},
            'Trae Young': {'adp': 18.8, 'adp_rank': 18},
            'Paolo Banchero': {'adp': 19.5, 'adp_rank': 19},
            'Devin Booker': {'adp': 20.3, 'adp_rank': 20},
            'Scottie Barnes': {'adp': 21.7, 'adp_rank': 21},
            'Chet Holmgren': {'adp': 22.4, 'adp_rank': 22},
            'Victor Wembanyama': {'adp': 23.1, 'adp_rank': 23},
            'Lauri Markkanen': {'adp': 24.8, 'adp_rank': 24},
            'Bam Adebayo': {'adp': 25.5, 'adp_rank': 25},
            'De\'Aaron Fox': {'adp': 26.9, 'adp_rank': 26},
            'Paul George': {'adp': 27.6, 'adp_rank': 27},
            'Jimmy Butler': {'adp': 28.3, 'adp_rank': 28},
            'Kawhi Leonard': {'adp': 29.7, 'adp_rank': 29},
            'Ja Morant': {'adp': 30.4, 'adp_rank': 30},
            'Zion Williamson': {'adp': 31.8, 'adp_rank': 31},
            'Jalen Brunson': {'adp': 32.5, 'adp_rank': 32},
            'Kyrie Irving': {'adp': 33.2, 'adp_rank': 33},
            'Franz Wagner': {'adp': 34.9, 'adp_rank': 34},
            'Alperen Sengun': {'adp': 35.6, 'adp_rank': 35},
            'Jaren Jackson Jr.': {'adp': 36.3, 'adp_rank': 36},
            'Pascal Siakam': {'adp': 37.7, 'adp_rank': 37},
            'Mikal Bridges': {'adp': 38.4, 'adp_rank': 38},
            'CJ McCollum': {'adp': 39.1, 'adp_rank': 39},
            'Nikola Vucevic': {'adp': 40.8, 'adp_rank': 40},
            'Myles Turner': {'adp': 41.5, 'adp_rank': 41},
            'Fred VanVleet': {'adp': 42.2, 'adp_rank': 42},
            'Jrue Holiday': {'adp': 43.6, 'adp_rank': 43},
            'Rudy Gobert': {'adp': 44.3, 'adp_rank': 44},
            'Desmond Bane': {'adp': 45.0, 'adp_rank': 45},
            'Jusuf Nurkic': {'adp': 100.2, 'adp_rank': 100}
        }

        # Normalize all keys in mock data
        normalized_adp = {}
        for name, data in mock_adp.items():
            normalized_adp[self._normalize_name(name)] = data

        return normalized_adp

    def _normalize_name(self, name: str) -> str:
        """Normalize player names for matching"""
        import unicodedata
        # Remove accents and special characters
        normalized = unicodedata.normalize('NFD', name)
        normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
        return normalized.lower().strip()

    def _merge_adp_data(self, players: List[Dict], adp_data: Dict[str, Dict]) -> List[Dict]:
        """Merge ADP data with player statistics"""
        # ADP data should already have normalized keys
        for player in players:
            normalized_player_name = self._normalize_name(player['name'])

            # Try normalized match (ADP data keys are already normalized)
            if normalized_player_name in adp_data:
                player['adp'] = adp_data[normalized_player_name]['adp']
                player['adp_rank'] = adp_data[normalized_player_name]['adp_rank']
            else:
                # For players not in top ADP, estimate based on their position in our data
                player['adp'] = None
                player['adp_rank'] = None

        # Sort by ADP rank for players that have it
        players_with_adp = [p for p in players if p['adp_rank'] is not None]
        players_without_adp = [p for p in players if p['adp_rank'] is None]

        # Assign estimated ADP ranks to remaining players
        start_rank = len(players_with_adp) + 1
        for i, player in enumerate(players_without_adp):
            player['adp_rank'] = start_rank + i
            player['adp'] = start_rank + i + 0.5  # Estimated ADP

        return players

    def _is_cache_valid(self, cache_file: str) -> bool:
        if not os.path.exists(cache_file):
            return False

        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        return datetime.now() - file_time < self.cache_duration