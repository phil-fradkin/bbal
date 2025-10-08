import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

class AuctionValueCalculator:
    def __init__(self):
        self.categories = ['points', 'rebounds', 'assists', 'steals', 'blocks',
                          'threes', 'fg_pct', 'ft_pct', 'turnovers']
        self.counting_cats = ['points', 'rebounds', 'assists', 'steals', 'blocks', 'threes']
        self.percentage_cats = ['fg_pct', 'ft_pct']
        self.negative_cats = ['turnovers']

        self.position_slots = {
            'PG': 1, 'SG': 1, 'SF': 1, 'PF': 1, 'C': 1,
            'G': 1, 'F': 1, 'UTIL': 2
        }

    def calculate_auction_values(
        self,
        players: List[Dict],
        punted_cats: List[str] = None,
        category_weights: Dict[str, float] = None,
        inflation_rate: float = 0.0,
        league_teams: int = 12,
        roster_size: int = 13,
        budget: int = 200,
        adp_weight: float = 0.5,  # How much to weight ADP vs z-scores in value calc
        min_games: int = 30  # Minimum games required for consideration
    ) -> List[Dict]:
        if not players:
            return []

        punted_cats = punted_cats or []
        category_weights = category_weights or {}
        df = pd.DataFrame(players)

        # Filter out players with too few games
        df = df[df['games'] >= min_games].copy()

        df = self._clean_positions(df)

        df = self._calculate_percentages(df)

        z_scores = self._calculate_z_scores(df, punted_cats, category_weights)

        replacement_level = self._calculate_replacement_level(
            z_scores, league_teams, roster_size
        )

        # Get ADP-based values and z-score based values
        z_score_values = self._calculate_values_above_replacement(
            z_scores, replacement_level, league_teams, budget
        )

        adp_values = self._calculate_adp_based_values(
            df, league_teams, budget
        )

        # Calculate punt aggressiveness (how much we're deviating from standard)
        punt_factor = 0
        for weight in category_weights.values():
            if weight == 0:
                punt_factor += 0.3  # Strong punt
            elif weight < 0.5:
                punt_factor += 0.15  # De-emphasis
            elif weight > 1.5:
                punt_factor += 0.1  # Strong emphasis

        # Reduce ADP influence when punting (use more z-scores)
        adjusted_adp_weight = max(0.2, adp_weight * (1 - min(0.5, punt_factor)))

        # Blend the two value systems
        values = self._blend_values(
            z_score_values, adp_values, df, adjusted_adp_weight
        )

        if inflation_rate > 0:
            values = self._apply_inflation(values, inflation_rate)

        result = []
        for idx, row in df.iterrows():
            player_dict = row.to_dict()
            player_dict['z_score_total'] = float(z_scores.loc[idx, 'total_z'])
            player_dict['auction_value'] = int(values.loc[idx])
            player_dict['value_rank'] = 0

            # Add individual category z-scores (use raw for display)
            for cat in self.categories:
                z_col_raw = f'z_{cat}_raw'
                z_col = f'z_{cat}'
                # Use raw z-scores for display purposes
                if z_col_raw in z_scores.columns:
                    player_dict[z_col] = float(z_scores.loc[idx, z_col_raw])

            # Convert numpy types to native Python types
            for key, value in player_dict.items():
                if hasattr(value, 'item'):  # numpy scalar
                    if 'int' in str(type(value)):
                        player_dict[key] = int(value)
                    else:
                        player_dict[key] = float(value)
                elif isinstance(value, (np.integer, np.int64)):
                    player_dict[key] = int(value)
                elif isinstance(value, (np.floating, np.float64)):
                    player_dict[key] = float(value)

            result.append(player_dict)

        result = sorted(result, key=lambda x: x['auction_value'], reverse=True)
        for i, player in enumerate(result):
            player['value_rank'] = i + 1

            # Calculate blended rank (ADP + Value Rank)
            # Weight ADP more heavily for top players
            adp_rank = player.get('adp_rank')
            value_rank = player['value_rank']

            if adp_rank and adp_rank <= 200:  # Only blend if we have real ADP data
                if adp_rank <= 20:
                    # Top 20: 35% ADP, 65% calculated
                    blend_weight = 0.35
                elif adp_rank <= 40:
                    # Top 40: 20% ADP, 80% calculated
                    blend_weight = 0.20
                elif adp_rank <= 60:
                    # Top 60: 10% ADP, 90% calculated
                    blend_weight = 0.10
                else:
                    # Beyond 60: 0% ADP, 100% calculated
                    blend_weight = 0.0

                player['blend_rank'] = (adp_rank * blend_weight) + (value_rank * (1 - blend_weight))
            else:
                # No ADP or very low - just use value rank
                player['blend_rank'] = value_rank

        # Re-sort by blend rank and assign final blend rankings
        result = sorted(result, key=lambda x: x['blend_rank'])
        for i, player in enumerate(result):
            player['blend_rank'] = i + 1

        # Re-sort back by value rank for display
        result = sorted(result, key=lambda x: x['value_rank'])

        return result

    def _clean_positions(self, df: pd.DataFrame) -> pd.DataFrame:
        def clean_pos(pos):
            if pd.isna(pos) or pos == '':
                return 'UTIL'
            pos = str(pos).upper().strip()
            if '-' in pos:
                pos = pos.split('-')[0]
            if pos in ['PG', 'SG', 'G']:
                return 'G'
            elif pos in ['SF', 'PF', 'F']:
                return 'F'
            elif pos in ['C']:
                return 'C'
            else:
                return 'UTIL'

        df['position_group'] = df['position'].apply(clean_pos)
        return df

    def _calculate_percentages(self, df: pd.DataFrame) -> pd.DataFrame:
        epsilon = 1e-6

        if 'total_fgm' in df.columns and 'total_fga' in df.columns:
            df['fg_pct_weighted'] = df['total_fgm'] / (df['total_fga'] + epsilon)
        else:
            df['fg_pct_weighted'] = df.get('fg_pct', 0)

        if 'total_ftm' in df.columns and 'total_fta' in df.columns:
            df['ft_pct_weighted'] = df['total_ftm'] / (df['total_fta'] + epsilon)
        else:
            df['ft_pct_weighted'] = df.get('ft_pct', 0)

        return df

    def _calculate_z_scores(self, df: pd.DataFrame, punted_cats: List[str], category_weights: Dict[str, float]) -> pd.DataFrame:
        z_scores = pd.DataFrame(index=df.index)

        # If no weights provided, use 1.0 for all non-punted categories
        default_weight = 1.0

        for cat in self.categories:
            # Skip punted categories (backward compatibility)
            if cat in punted_cats:
                continue

            # Get weight for this category (default to 1.0 if not specified)
            weight = category_weights.get(cat, default_weight)

            # Skip categories with 0 weight
            if weight == 0:
                continue

            if cat in self.counting_cats:
                # Use per-game averages instead of totals
                # This ensures fair comparison regardless of games played
                if cat in df.columns:
                    values = df[cat]  # Already per-game
                else:
                    # Convert totals to per-game if needed
                    col_name = f'total_{cat}'
                    if col_name in df.columns:
                        values = df[col_name] / df['games']
                    else:
                        values = df.get(cat, 0)
            elif cat == 'fg_pct':
                values = df['fg_pct_weighted']
            elif cat == 'ft_pct':
                values = df['ft_pct_weighted']
            elif cat == 'turnovers':
                # Use per-game turnovers (negative impact)
                if 'turnovers' in df.columns:
                    values = -df['turnovers']  # Already per-game
                elif 'total_turnovers' in df.columns:
                    values = -(df['total_turnovers'] / df['games'])
                else:
                    values = -df.get('turnovers', 0)
            else:
                values = df[cat]

            mean_val = values.mean()
            std_val = values.std()

            if std_val > 0:
                # Calculate raw z-score
                raw_z = (values - mean_val) / std_val

                # Apply non-linear scaling for punts (exponential scaling)
                # This makes punt decisions more impactful
                if weight == 0:
                    # Completely punted - severe penalty for good performance
                    weighted_z = raw_z * -0.5 if raw_z > 0 else 0
                elif weight < 0.5:
                    # De-emphasized - exponential penalty
                    weighted_z = raw_z * (weight ** 2)
                elif weight > 1.5:
                    # Emphasized - exponential bonus
                    weighted_z = raw_z * (weight ** 1.5)
                else:
                    # Normal weight - standard linear
                    weighted_z = raw_z * weight

                # Store both raw and weighted z-scores
                z_scores[f'z_{cat}_raw'] = raw_z  # For display
                z_scores[f'z_{cat}'] = weighted_z  # For calculation
            else:
                z_scores[f'z_{cat}_raw'] = 0
                z_scores[f'z_{cat}'] = 0

        # Only sum the weighted z-scores (not the raw ones)
        z_score_cols = [col for col in z_scores.columns if col.startswith('z_') and not col.endswith('_raw')]
        z_scores['total_z'] = z_scores[z_score_cols].sum(axis=1)

        # Add specialist bonus for players who excel in targeted categories
        # This makes specialists more valuable in punt builds
        specialist_bonus = 0
        for cat in self.categories:
            weight = category_weights.get(cat, default_weight)
            if weight >= 1.5:  # Highly targeted category
                raw_col = f'z_{cat}_raw'
                if raw_col in z_scores.columns:
                    # Give bonus to players who are elite (z > 1.5) in targeted categories
                    elite_bonus = z_scores[raw_col].apply(lambda x: max(0, x - 1.5) * 0.5 if x > 1.5 else 0)
                    specialist_bonus += elite_bonus * weight

        z_scores['total_z'] = z_scores['total_z'] + specialist_bonus

        z_scores['position_group'] = df['position_group']
        z_scores['name'] = df['name']
        z_scores['games'] = df['games']

        return z_scores

    def _calculate_replacement_level(
        self,
        z_scores: pd.DataFrame,
        league_teams: int,
        roster_size: int
    ) -> float:
        total_rostered = league_teams * roster_size

        # Use average of players around the replacement level for stability
        sorted_players = z_scores.sort_values('total_z', ascending=False)

        if len(sorted_players) >= total_rostered + 10:
            # Take average of players ranked 130-150 (more aggressive replacement level)
            # This provides more stable replacement level and reduces total VAR
            start_idx = max(0, total_rostered - 26)  # 130th player (156 - 26)
            end_idx = min(len(sorted_players), total_rostered - 6)  # 150th player (156 - 6)

            replacement_range = sorted_players.iloc[start_idx:end_idx]['total_z']
            replacement_level = replacement_range.mean()
        elif len(sorted_players) >= total_rostered:
            # Not enough players for averaging, use the traditional method
            replacement_level = sorted_players.iloc[total_rostered]['total_z']
        else:
            # If we don't have enough players, use the last one
            replacement_level = sorted_players.iloc[-1]['total_z'] if len(sorted_players) > 0 else 0

        return replacement_level

    def _calculate_values_above_replacement(
        self,
        z_scores: pd.DataFrame,
        replacement_level: float,
        league_teams: int,
        budget: int
    ) -> pd.Series:
        var_scores = z_scores['total_z'] - replacement_level

        var_scores[var_scores < 0] = 0

        # Boost VAR importance for top 80 players
        # This increases their share of the value pool
        sorted_indices = var_scores.nlargest(80).index
        scaled_var_scores = var_scores.copy()

        for idx in sorted_indices:
            # Apply 1.5x multiplier to top 80 players' VAR
            scaled_var_scores[idx] = var_scores[idx] * 1.5

        top_players = int(league_teams * 13)

        # Only the top N players get rostered and have real value
        # Sum VAR only for rosterable players (use scaled values)
        top_var_scores = scaled_var_scores.nlargest(top_players)
        total_var = top_var_scores.sum()
        total_dollars = league_teams * budget - top_players

        if total_var > 0:
            dollar_per_var = total_dollars / total_var
            # Apply dollar per VAR using scaled VAR scores
            values = scaled_var_scores * dollar_per_var + 1
        else:
            values = pd.Series(1, index=var_scores.index)

        values[values < 1] = 1

        values = values.round().astype(int)

        return values

    def _apply_inflation(self, values: pd.Series, inflation_rate: float) -> pd.Series:
        inflated_values = values * (1 + inflation_rate / 100)
        inflated_values = inflated_values.round().astype(int)
        inflated_values[inflated_values < 1] = 1
        return inflated_values

    def _calculate_adp_based_values(
        self,
        df: pd.DataFrame,
        league_teams: int,
        budget: int
    ) -> pd.Series:
        """Calculate auction values based purely on ADP rankings"""
        total_budget = league_teams * budget
        roster_spots = league_teams * 13

        # Create a value curve based on ADP rank
        # Top players get more budget, declining curve
        values = pd.Series(1, index=df.index)

        for idx in df.index:
            adp_rank = df.loc[idx, 'adp_rank'] if 'adp_rank' in df.columns else None

            if adp_rank and adp_rank <= roster_spots:
                # Use a declining curve: more money for top players
                # Updated for higher top-end values with progressive decline
                if adp_rank <= 5:
                    base_value = 75 - (adp_rank - 1) * 4  # $75, $71, $67, $63, $59
                elif adp_rank <= 10:
                    base_value = 59 - (adp_rank - 5) * 5  # $54, $49, $44, $39, $34
                elif adp_rank <= 20:
                    base_value = 34 - (adp_rank - 10) * 2  # $32, $30, $28... down to $14
                elif adp_rank <= 40:
                    base_value = 14 - (adp_rank - 20) * 0.4  # $13.6, $13.2... down to $6
                elif adp_rank <= 80:
                    base_value = 6 - (adp_rank - 40) * 0.075  # $5.9, $5.8... down to $3
                elif adp_rank <= 120:
                    base_value = 3 - (adp_rank - 80) * 0.05  # $2.95, $2.90... down to $1
                else:
                    base_value = 1

                values.loc[idx] = max(1, int(base_value))
            else:
                values.loc[idx] = 1

        return values

    def _blend_values(
        self,
        z_score_values: pd.Series,
        adp_values: pd.Series,
        df: pd.DataFrame,
        adp_weight: float
    ) -> pd.Series:
        """Blend z-score and ADP-based values with variable weighting"""
        blended = pd.Series(1, index=z_score_values.index)

        for idx in z_score_values.index:
            adp_rank = df.loc[idx, 'adp_rank'] if 'adp_rank' in df.columns else None

            if adp_rank and adp_rank <= 200:
                # Variable weighting based on ADP rank - reduced ADP influence
                if adp_rank <= 20:
                    # Top 20: 35% ADP weight
                    weight = 0.35
                elif adp_rank <= 40:
                    # Top 40: 20% ADP weight
                    weight = 0.20
                elif adp_rank <= 60:
                    # Top 60: 10% ADP weight
                    weight = 0.10
                else:
                    # Beyond 60: 0% ADP weight (pure z-scores)
                    weight = 0.0

                # Blend the values
                blended_value = (adp_values.loc[idx] * weight +
                                z_score_values.loc[idx] * (1 - weight))
                blended.loc[idx] = max(1, int(round(blended_value)))
            else:
                # No ADP data, use pure z-score value
                blended.loc[idx] = z_score_values.loc[idx]

        return blended