export interface Player {
  name: string;
  team: string;
  position: string;
  games: number;
  minutes: number;
  points: number;
  rebounds: number;
  assists: number;
  steals: number;
  blocks: number;
  threes: number;
  fgm: number;
  fga: number;
  ftm: number;
  fta: number;
  turnovers: number;
  fg_pct: number;
  ft_pct: number;
  total_points: number;
  total_rebounds: number;
  total_assists: number;
  total_steals: number;
  total_blocks: number;
  total_threes: number;
  total_turnovers: number;
  z_score_total?: number;
  auction_value?: number;
  value_rank?: number;
  // Individual category z-scores
  z_points?: number;
  z_rebounds?: number;
  z_assists?: number;
  z_steals?: number;
  z_blocks?: number;
  z_threes?: number;
  z_fg_pct?: number;
  z_ft_pct?: number;
  z_turnovers?: number;
  // ADP data
  adp?: number;
  adp_rank?: number;
  // Blended ranking
  blend_rank?: number;
}