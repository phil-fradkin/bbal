import { useState } from 'react';
import axios from 'axios';
import { PlayerTable } from './components/PlayerTable';
import { Player } from './types/Player';
import API_URL from './config/api';

const CATEGORIES = [
  'points', 'rebounds', 'assists', 'steals', 'blocks',
  'threes', 'fg_pct', 'ft_pct', 'turnovers'
];

interface DraftedPlayer extends Player {
  actualPrice?: number;
}

function App() {
  const [players, setPlayers] = useState<Player[]>([]);
  const [myTeam, setMyTeam] = useState<DraftedPlayer[]>([]);
  const [othersDrafted, setOthersDrafted] = useState<DraftedPlayer[]>([]);
  const [viewMode, setViewMode] = useState<'available' | 'myteam' | 'others'>('available');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [season, setSeason] = useState('2025');
  const [minGames, setMinGames] = useState(20);
  const [leagueTeams, setLeagueTeams] = useState(12);
  const [rosterSize, setRosterSize] = useState(13);
  const [budget, setBudget] = useState(200);
  const [inflationRate, setInflationRate] = useState(0);
  const [categoryWeights, setCategoryWeights] = useState<Record<string, number>>({
    points: 1.0,
    rebounds: 1.0,
    assists: 1.0,
    steals: 1.0,
    blocks: 1.0,
    threes: 1.0,
    fg_pct: 1.0,
    ft_pct: 1.0,
    turnovers: 1.0
  });

  const handleWeightChange = (category: string, weight: number) => {
    setCategoryWeights(prev => ({
      ...prev,
      [category]: weight
    }));
  };

  const handleDraftToMyTeam = (player: Player, actualPrice?: number) => {
    setPlayers(prev => prev.filter(p => p.name !== player.name));
    const draftedPlayer: DraftedPlayer = { ...player, actualPrice: actualPrice || player.auction_value };
    setMyTeam(prev => [...prev, draftedPlayer]);
  };

  const handleDraftToOthers = (player: Player) => {
    setPlayers(prev => prev.filter(p => p.name !== player.name));
    setOthersDrafted(prev => [...prev, player]);
  };

  const handleUndraftFromMyTeam = (player: Player) => {
    setMyTeam(prev => prev.filter(p => p.name !== player.name));
    setPlayers(prev => [...prev, player].sort((a, b) => (b.auction_value || 0) - (a.auction_value || 0)));
  };

  const handleUndraftFromOthers = (player: Player) => {
    setOthersDrafted(prev => prev.filter(p => p.name !== player.name));
    setPlayers(prev => [...prev, player].sort((a, b) => (b.auction_value || 0) - (a.auction_value || 0)));
  };

  const clearAllDrafted = () => {
    setPlayers(prev => [...prev, ...myTeam, ...othersDrafted].sort((a, b) => (b.auction_value || 0) - (a.auction_value || 0)));
    setMyTeam([]);
    setOthersDrafted([]);
  };

  const totalSpent = myTeam.reduce((sum, player) => sum + (player.actualPrice || player.auction_value || 0), 0);
  const remainingBudget = budget - totalSpent;
  const avgPlayerPrice = myTeam.length > 0 ? totalSpent / myTeam.length : 0;
  const remainingRosterSpots = rosterSize - myTeam.length;

  const calculateValues = async () => {
    setLoading(true);
    setError(null);

    try {
      const baseURL = import.meta.env.MODE === 'production' ? API_URL : '/api';
      const response = await axios.post(`${baseURL}/calculate`, {
        season,
        min_games: minGames,
        category_weights: categoryWeights,
        inflation_rate: inflationRate,
        league_teams: leagueTeams,
        roster_size: rosterSize,
        budget
      });

      setPlayers(response.data);
    } catch (err) {
      setError('Failed to calculate values. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const exportToCSV = async () => {
    if (players.length === 0) return;

    try {
      const response = await axios.post('/api/export/csv', players, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `nba_auction_values_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export CSV');
      console.error(err);
    }
  };

  const exportToJSON = async () => {
    if (players.length === 0) return;

    try {
      const response = await axios.post('/api/export/json', players, {
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `nba_auction_values_${new Date().toISOString().split('T')[0]}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to export JSON');
      console.error(err);
    }
  };

  const copyToClipboard = () => {
    if (players.length === 0) return;

    const headers = ['Rank', 'Name', 'Team', 'Position', 'Value'];
    const rows = players.map((p, i) =>
      `${p.value_rank || i + 1}\t${p.name}\t${p.team}\t${p.position}\t$${p.auction_value || 1}`
    );

    const text = [headers.join('\t'), ...rows].join('\n');
    navigator.clipboard.writeText(text)
      .then(() => alert('Copied to clipboard!'))
      .catch(err => {
        setError('Failed to copy to clipboard');
        console.error(err);
      });
  };

  return (
    <div className="App">
      <header className="header">
        <h1>NBA Fantasy Auction Value Calculator</h1>
        <p>Calculate 9-cat auction values with punt strategies and market inflation</p>
      </header>

      <div className="container">
        <div className="controls">
          <div className="controls-grid">
            <div className="control-group">
              <label htmlFor="season">Season</label>
              <input
                id="season"
                type="text"
                value={season}
                onChange={(e) => setSeason(e.target.value)}
              />
            </div>

            <div className="control-group">
              <label htmlFor="minGames">Min Games</label>
              <input
                id="minGames"
                type="number"
                value={minGames}
                onChange={(e) => setMinGames(parseInt(e.target.value) || 0)}
              />
            </div>

            <div className="control-group">
              <label htmlFor="leagueTeams">League Teams</label>
              <input
                id="leagueTeams"
                type="number"
                value={leagueTeams}
                onChange={(e) => setLeagueTeams(parseInt(e.target.value) || 12)}
              />
            </div>

            <div className="control-group">
              <label htmlFor="rosterSize">Roster Size</label>
              <input
                id="rosterSize"
                type="number"
                value={rosterSize}
                onChange={(e) => setRosterSize(parseInt(e.target.value) || 13)}
              />
            </div>

            <div className="control-group">
              <label htmlFor="budget">Budget</label>
              <input
                id="budget"
                type="number"
                value={budget}
                onChange={(e) => setBudget(parseInt(e.target.value) || 200)}
              />
            </div>

            <div className="control-group">
              <label htmlFor="inflation">Inflation Rate</label>
              <div className="inflation-display">
                <input
                  id="inflation"
                  type="range"
                  min="0"
                  max="50"
                  value={inflationRate}
                  onChange={(e) => setInflationRate(parseFloat(e.target.value))}
                />
                <span className="inflation-value">{inflationRate}%</span>
              </div>
            </div>
          </div>

          <div className="category-weights">
            <h3>Category Weights</h3>
            <div className="weights-grid">
              {CATEGORIES.map(cat => {
                const weight = categoryWeights[cat];
                const bgColor = weight === 0 ? '#fee2e2' :
                               weight < 0.5 ? '#fef3c7' :
                               weight < 1 ? '#dbeafe' :
                               weight === 1 ? 'transparent' :
                               weight < 1.5 ? '#dcfce7' : '#c7f9cc';

                return (
                  <div key={cat} className="weight-control">
                    <label className="weight-label">
                      {cat.replace('_', ' ').toUpperCase()}:
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="2"
                      step="0.1"
                      value={weight}
                      onChange={(e) => handleWeightChange(cat, parseFloat(e.target.value) || 0)}
                      className="weight-input"
                      style={{
                        backgroundColor: bgColor,
                        fontWeight: weight === 0 || weight >= 1.5 ? '600' : '400'
                      }}
                    />
                  </div>
                );
              })}
            </div>
            <div className="weight-presets">
              <h4>Quick Presets:</h4>
              <button className="btn btn-secondary" onClick={() => setCategoryWeights(Object.fromEntries(CATEGORIES.map(c => [c, 1.0])))}>Balanced</button>
              <button className="btn btn-secondary" onClick={() => setCategoryWeights({...categoryWeights, turnovers: 0, fg_pct: 0, ft_pct: 0})}>Punt %s & TO</button>
              <button className="btn btn-secondary" onClick={() => setCategoryWeights({...categoryWeights, assists: 0, steals: 0})}>Punt AST/STL</button>
              <button className="btn btn-secondary" onClick={() => setCategoryWeights({...categoryWeights, rebounds: 0, blocks: 0, fg_pct: 0})}>Punt REB/BLK/FG%</button>
              <button className="btn btn-secondary" onClick={() => setCategoryWeights({...categoryWeights, points: 0, threes: 0, ft_pct: 0})}>Punt PTS/3s/FT%</button>
            </div>
          </div>

          <div className="action-buttons">
            <button className="btn btn-primary" onClick={calculateValues}>
              Calculate Values
            </button>
            {(players.length > 0 || myTeam.length > 0 || othersDrafted.length > 0) && (
              <>
                <button
                  className={`btn ${viewMode === 'available' ? 'btn-success' : 'btn-secondary'}`}
                  onClick={() => setViewMode('available')}
                >
                  Available ({players.length})
                </button>
                <button
                  className={`btn ${viewMode === 'myteam' ? 'btn-success' : 'btn-secondary'}`}
                  onClick={() => setViewMode('myteam')}
                >
                  My Team ({myTeam.length})
                </button>
                <button
                  className={`btn ${viewMode === 'others' ? 'btn-success' : 'btn-secondary'}`}
                  onClick={() => setViewMode('others')}
                >
                  Others ({othersDrafted.length})
                </button>
                {(myTeam.length > 0 || othersDrafted.length > 0) && (
                  <button className="btn btn-secondary" onClick={clearAllDrafted}>
                    Clear All
                  </button>
                )}
                <button className="btn btn-secondary" onClick={exportToCSV}>
                  Export CSV
                </button>
                <button className="btn btn-secondary" onClick={exportToJSON}>
                  Export JSON
                </button>
                <button className="btn btn-success" onClick={copyToClipboard}>
                  Copy to Clipboard
                </button>
              </>
            )}
          </div>
        </div>

        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {myTeam.length > 0 && (
          <>
            <div className="draft-summary">
              <h3>My Team Summary</h3>
              <div className="summary-stats">
                <div className="stat-item">
                  <span className="stat-label">Players:</span>
                  <span className="stat-value">{myTeam.length}/{rosterSize}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Spent:</span>
                  <span className={`stat-value ${remainingBudget < 0 ? 'over-budget' : ''}`}>${totalSpent}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Budget Left:</span>
                  <span className={`stat-value ${remainingBudget < 0 ? 'over-budget' : ''}`}>${remainingBudget}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Avg Price:</span>
                  <span className="stat-value">${avgPlayerPrice.toFixed(1)}</span>
                </div>
                <div className="stat-item">
                  <span className="stat-label">Max Bid:</span>
                  <span className="stat-value">${remainingRosterSpots > 0 ? Math.max(1, remainingBudget - remainingRosterSpots + 1) : 0}</span>
                </div>
              </div>
            </div>

            <div className="team-category-summary">
              <h3>Team Category Strengths</h3>
              <div className="category-stats-grid">
                {CATEGORIES.map(cat => {
                  const zKey = `z_${cat}` as keyof DraftedPlayer;
                  const avgZ = myTeam.reduce((sum, p) => sum + ((p[zKey] as number) || 0), 0) / myTeam.length;

                  let strengthClass = '';
                  let strengthLabel = '';

                  if (avgZ >= 1.0) {
                    strengthClass = 'cat-elite';
                    strengthLabel = 'Elite';
                  } else if (avgZ >= 0.5) {
                    strengthClass = 'cat-strong';
                    strengthLabel = 'Strong';
                  } else if (avgZ >= 0) {
                    strengthClass = 'cat-above';
                    strengthLabel = 'Above Avg';
                  } else if (avgZ >= -0.5) {
                    strengthClass = 'cat-below';
                    strengthLabel = 'Below Avg';
                  } else {
                    strengthClass = 'cat-weak';
                    strengthLabel = 'Weak';
                  }

                  return (
                    <div key={cat} className={`category-stat-item ${strengthClass}`}>
                      <div className="cat-name">{cat.replace('_', ' ').toUpperCase()}</div>
                      <div className="cat-z-score">{avgZ >= 0 ? '+' : ''}{avgZ.toFixed(2)}</div>
                      <div className="cat-strength">{strengthLabel}</div>
                    </div>
                  );
                })}
              </div>
              <div className="team-total-z">
                <span className="total-z-label">Team Total Z-Score:</span>
                <span className="total-z-value">
                  {myTeam.reduce((sum, p) => sum + (p.z_score_total || 0), 0).toFixed(1)}
                </span>
                <span className="total-z-avg">
                  (Avg: {(myTeam.reduce((sum, p) => sum + (p.z_score_total || 0), 0) / myTeam.length).toFixed(2)})
                </span>
              </div>
            </div>
          </>
        )}

        <PlayerTable
          players={
            viewMode === 'myteam' ? myTeam :
            viewMode === 'others' ? othersDrafted :
            players
          }
          loading={loading}
          onDraftToMyTeam={viewMode === 'available' ? handleDraftToMyTeam : undefined}
          onDraftToOthers={viewMode === 'available' ? handleDraftToOthers : undefined}
          onUndraft={
            viewMode === 'myteam' ? handleUndraftFromMyTeam :
            viewMode === 'others' ? handleUndraftFromOthers :
            undefined
          }
          viewMode={viewMode}
        />
      </div>
    </div>
  );
}

export default App;