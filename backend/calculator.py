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
        adp_weight: float = 0.5  # How much to weight ADP vs z-scores in value calc
    ) -> List[Dict]:
        if not players:
            return []

        punted_cats = punted_cats or []
        category_weights = category_weights or {}
        df = pd.DataFrame(players)

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

        # Blend the two value systems
        values = self._blend_values(
            z_score_values, adp_values, df, adp_weight
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
                    # Top 20: 70% ADP, 30% calculated
                    blend_weight = 0.7
                elif adp_rank <= 50:
                    # Top 50: 60% ADP, 40% calculated
                    blend_weight = 0.6
                elif adp_rank <= 100:
                    # Top 100: 50% ADP, 50% calculated
                    blend_weight = 0.5
                else:
                    # Beyond 100: 40% ADP, 60% calculated
                    blend_weight = 0.4

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
                col_name = f'total_{cat}'
                if col_name in df.columns:
                    values = df[col_name]
                else:
                    values = df[cat] * df['games']
            elif cat == 'fg_pct':
                values = df['fg_pct_weighted']
            elif cat == 'ft_pct':
                values = df['ft_pct_weighted']
            elif cat == 'turnovers':
                if 'total_turnovers' in df.columns:
                    values = -df['total_turnovers']
                else:
                    values = -(df['turnovers'] * df['games'])
            else:
                values = df[cat]

            mean_val = values.mean()
            std_val = values.std()

            if std_val > 0:
                # Calculate raw z-score
                raw_z = (values - mean_val) / std_val
                # Store both raw and weighted z-scores
                z_scores[f'z_{cat}_raw'] = raw_z  # For display
                z_scores[f'z_{cat}'] = raw_z * weight  # For calculation
            else:
                z_scores[f'z_{cat}_raw'] = 0
                z_scores[f'z_{cat}'] = 0

        # Only sum the weighted z-scores (not the raw ones)
        z_score_cols = [col for col in z_scores.columns if col.startswith('z_') and not col.endswith('_raw')]
        z_scores['total_z'] = z_scores[z_score_cols].sum(axis=1)

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

        # Simple approach: replacement level is the last rostered player
        sorted_players = z_scores.sort_values('total_z', ascending=False)

        if len(sorted_players) >= total_rostered:
            # Replacement level is the player just outside the roster cutoff
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

        top_players = int(league_teams * 13)
        top_var = var_scores.nlargest(top_players)

        total_var = top_var.sum()
        total_dollars = league_teams * budget - top_players

        if total_var > 0:
            dollar_per_var = total_dollars / total_var
            values = var_scores * dollar_per_var + 1
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
                # Approximate auction values based on typical drafts
                if adp_rank <= 5:
                    base_value = 55 - (adp_rank - 1) * 3
                elif adp_rank <= 10:
                    base_value = 43 - (adp_rank - 5) * 4
                elif adp_rank <= 20:
                    base_value = 23 - (adp_rank - 10) * 1.5
                elif adp_rank <= 40:
                    base_value = 10 - (adp_rank - 20) * 0.3
                elif adp_rank <= 80:
                    base_value = 4 - (adp_rank - 40) * 0.05
                elif adp_rank <= 120:
                    base_value = 2 - (adp_rank - 80) * 0.025
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
                # Variable weighting based on ADP rank
                if adp_rank <= 20:
                    # Top 20: heavily weight ADP (70%)
                    weight = 0.7
                elif adp_rank <= 50:
                    # Top 50: balanced weight (60% ADP)
                    weight = 0.6
                elif adp_rank <= 100:
                    # Top 100: slight ADP preference (50%)
                    weight = 0.5
                else:
                    # Beyond 100: favor z-scores (30% ADP)
                    weight = 0.3

                # Blend the values
                blended_value = (adp_values.loc[idx] * weight +
                                z_score_values.loc[idx] * (1 - weight))
                blended.loc[idx] = max(1, int(round(blended_value)))
            else:
                # No ADP data, use pure z-score value
                blended.loc[idx] = z_score_values.loc[idx]

        return blended