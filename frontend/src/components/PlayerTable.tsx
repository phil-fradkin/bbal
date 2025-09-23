import React, { useState, useMemo } from 'react';
import { Player } from '../types/Player';
import { ZScoreCell } from './ZScoreCell';
import { StatCell } from './StatCell';

interface PlayerTableProps {
  players: Player[];
  loading: boolean;
  onDraftToMyTeam?: (player: Player, actualPrice?: number) => void;
  onDraftToOthers?: (player: Player) => void;
  onUndraft?: (player: Player) => void;
  viewMode?: 'available' | 'myteam' | 'others';
}

type SortKey = keyof Player | null;
type SortDirection = 'asc' | 'desc';

export const PlayerTable: React.FC<PlayerTableProps> = ({ players, loading, onDraftToMyTeam, onDraftToOthers, onUndraft, viewMode }) => {
  const [nameFilter, setNameFilter] = useState('');
  const [teamFilter, setTeamFilter] = useState('');
  const [positionFilter, setPositionFilter] = useState('');
  const [minValue, setMinValue] = useState('');
  const [sortKey, setSortKey] = useState<SortKey>('auction_value');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [showZScores, setShowZScores] = useState(false);
  const [draftingPlayer, setDraftingPlayer] = useState<Player | null>(null);
  const [actualPrice, setActualPrice] = useState<string>('');

  const handleSort = (key: keyof Player) => {
    if (sortKey === key) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('desc');
    }
  };

  const filteredAndSortedPlayers = useMemo(() => {
    let filtered = [...players];

    if (nameFilter) {
      filtered = filtered.filter(p =>
        p.name.toLowerCase().includes(nameFilter.toLowerCase())
      );
    }

    if (teamFilter) {
      filtered = filtered.filter(p =>
        p.team.toLowerCase().includes(teamFilter.toLowerCase())
      );
    }

    if (positionFilter) {
      filtered = filtered.filter(p =>
        p.position.toLowerCase().includes(positionFilter.toLowerCase())
      );
    }

    if (minValue) {
      const min = parseFloat(minValue);
      filtered = filtered.filter(p => (p.auction_value || 0) >= min);
    }

    if (sortKey) {
      filtered.sort((a, b) => {
        const aVal = a[sortKey] as number;
        const bVal = b[sortKey] as number;

        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        if (sortDirection === 'asc') {
          return aVal - bVal;
        } else {
          return bVal - aVal;
        }
      });
    }

    return filtered;
  }, [players, nameFilter, teamFilter, positionFilter, minValue, sortKey, sortDirection]);

  if (loading) {
    return <div className="loading">Loading player data...</div>;
  }

  const formatNumber = (num: number | undefined, decimals: number = 1): string => {
    if (num === undefined) return '-';
    return num.toFixed(decimals);
  };

  const handleDraftClick = (player: Player) => {
    setDraftingPlayer(player);
    setActualPrice(String(player.auction_value || 1));
  };

  const confirmDraft = () => {
    if (draftingPlayer && onDraftToMyTeam) {
      onDraftToMyTeam(draftingPlayer, parseInt(actualPrice) || draftingPlayer.auction_value);
      setDraftingPlayer(null);
      setActualPrice('');
    }
  };

  const cancelDraft = () => {
    setDraftingPlayer(null);
    setActualPrice('');
  };

  return (
    <div className="table-container">
      <div className="filters">
        <input
          type="text"
          className="filter-input"
          placeholder="Filter by name..."
          value={nameFilter}
          onChange={(e) => setNameFilter(e.target.value)}
        />
        <input
          type="text"
          className="filter-input"
          placeholder="Filter by team..."
          value={teamFilter}
          onChange={(e) => setTeamFilter(e.target.value)}
        />
        <input
          type="text"
          className="filter-input"
          placeholder="Filter by position..."
          value={positionFilter}
          onChange={(e) => setPositionFilter(e.target.value)}
        />
        <input
          type="number"
          className="filter-input"
          placeholder="Min value..."
          value={minValue}
          onChange={(e) => setMinValue(e.target.value)}
        />
        <button
          className={`btn ${showZScores ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setShowZScores(!showZScores)}
          style={{ marginLeft: '10px', padding: '8px 16px', fontSize: '14px' }}
        >
          {showZScores ? 'Show Stats' : 'Show Z-Scores'}
        </button>
      </div>

      <table className="player-table">
        <thead>
          <tr>
            <th onClick={() => handleSort('value_rank')}>Rank</th>
            <th onClick={() => handleSort('blend_rank')}>Blend</th>
            <th onClick={() => handleSort('adp_rank')}>ADP</th>
            <th onClick={() => handleSort('name')}>Name</th>
            <th onClick={() => handleSort('team')}>Team</th>
            <th onClick={() => handleSort('position')}>Pos</th>
            <th onClick={() => handleSort('games')}>GP</th>
            <th onClick={() => handleSort('auction_value')}>{viewMode === 'myteam' ? 'Value/Paid' : 'Value'}</th>
            <th onClick={() => handleSort('points')}>PTS</th>
            <th onClick={() => handleSort('rebounds')}>REB</th>
            <th onClick={() => handleSort('assists')}>AST</th>
            <th onClick={() => handleSort('steals')}>STL</th>
            <th onClick={() => handleSort('blocks')}>BLK</th>
            <th onClick={() => handleSort('threes')}>3PM</th>
            <th onClick={() => handleSort('fg_pct')}>FG%</th>
            <th onClick={() => handleSort('ft_pct')}>FT%</th>
            <th onClick={() => handleSort('turnovers')}>TO</th>
            <th onClick={() => handleSort('z_score_total')}>Z-Score</th>
            {(onDraftToMyTeam || onDraftToOthers || onUndraft) && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {filteredAndSortedPlayers.map((player, index) => (
            <tr
              key={`${player.name}-${index}`}
              style={{
                opacity: viewMode === 'others' ? 0.7 : 1
              }}
            >
              <td>{player.value_rank || index + 1}</td>
              <td>
                {player.blend_rank ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <span style={{ fontWeight: '700', fontSize: '15px' }}>{player.blend_rank}</span>
                    {Math.abs((player.value_rank || index + 1) - player.blend_rank) >= 5 && (
                      <span style={{
                        fontSize: '10px',
                        color: (player.value_rank || index + 1) > player.blend_rank ? '#059669' : '#dc2626'
                      }}>
                        {(player.value_rank || index + 1) > player.blend_rank ? '▲' : '▼'}
                        {Math.abs((player.value_rank || index + 1) - player.blend_rank)}
                      </span>
                    )}
                  </div>
                ) : (
                  '-'
                )}
              </td>
              <td>
                {player.adp_rank ? (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <span style={{ fontWeight: '600' }}>{player.adp_rank}</span>
                    {player.adp && player.adp <= 40 && (
                      <span style={{ fontSize: '10px', color: '#6b7280' }}>({player.adp.toFixed(1)})</span>
                    )}
                    {Math.abs((player.value_rank || index + 1) - (player.adp_rank || 0)) >= 10 && (
                      <span style={{
                        fontSize: '10px',
                        color: (player.value_rank || index + 1) < (player.adp_rank || 0) ? '#059669' : '#dc2626'
                      }}>
                        {(player.value_rank || index + 1) < (player.adp_rank || 0) ? '▲' : '▼'}
                        {Math.abs((player.value_rank || index + 1) - (player.adp_rank || 0))}
                      </span>
                    )}
                  </div>
                ) : (
                  '-'
                )}
              </td>
              <td>{player.name}</td>
              <td>{player.team}</td>
              <td>{player.position}</td>
              <td>{player.games}</td>
              <td className="value-cell">
                {viewMode === 'myteam' && (player as any).actualPrice ? (
                  <>
                    ${player.auction_value || 1} / <strong>${(player as any).actualPrice}</strong>
                    {(player as any).actualPrice < (player.auction_value || 1) &&
                      <span style={{ color: '#059669', marginLeft: '4px' }}>✓</span>
                    }
                    {(player as any).actualPrice > (player.auction_value || 1) &&
                      <span style={{ color: '#dc2626', marginLeft: '4px' }}>↑</span>
                    }
                  </>
                ) : (
                  `$${player.auction_value || 1}`
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_points} />
                ) : (
                  <StatCell
                    value={formatNumber(player.points)}
                    zScore={player.z_points}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_rebounds} />
                ) : (
                  <StatCell
                    value={formatNumber(player.rebounds)}
                    zScore={player.z_rebounds}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_assists} />
                ) : (
                  <StatCell
                    value={formatNumber(player.assists)}
                    zScore={player.z_assists}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_steals} />
                ) : (
                  <StatCell
                    value={formatNumber(player.steals)}
                    zScore={player.z_steals}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_blocks} />
                ) : (
                  <StatCell
                    value={formatNumber(player.blocks)}
                    zScore={player.z_blocks}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_threes} />
                ) : (
                  <StatCell
                    value={formatNumber(player.threes)}
                    zScore={player.z_threes}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_fg_pct} />
                ) : (
                  <StatCell
                    value={formatNumber(player.fg_pct * 100, 1)}
                    zScore={player.z_fg_pct}
                    isPercentage={true}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_ft_pct} />
                ) : (
                  <StatCell
                    value={formatNumber(player.ft_pct * 100, 1)}
                    zScore={player.z_ft_pct}
                    isPercentage={true}
                  />
                )}
              </td>
              <td>
                {showZScores ? (
                  <ZScoreCell value={player.z_turnovers} isNegativeCategory={true} />
                ) : (
                  <StatCell
                    value={formatNumber(player.turnovers)}
                    zScore={player.z_turnovers}
                    isNegativeCategory={true}
                  />
                )}
              </td>
              <td>{formatNumber(player.z_score_total, 2)}</td>
              {(onDraftToMyTeam || onDraftToOthers || onUndraft) && (
                <td className="action-buttons-cell">
                  {onDraftToMyTeam && onDraftToOthers && (
                    <>
                      <button
                        className="btn-action btn-draft-mine"
                        onClick={() => handleDraftClick(player)}
                        title="Draft to my team"
                      >
                        Mine
                      </button>
                      <button
                        className="btn-action btn-draft-others"
                        onClick={() => onDraftToOthers(player)}
                        title="Mark as drafted by others"
                      >
                        Others
                      </button>
                    </>
                  )}
                  {onUndraft && (
                    <button
                      className="btn-action btn-undraft"
                      onClick={() => onUndraft(player)}
                      title="Return to available"
                    >
                      Undo
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>

      {draftingPlayer && (
        <div className="draft-modal-overlay" onClick={cancelDraft}>
          <div className="draft-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Draft {draftingPlayer.name}</h3>
            <p>Suggested Value: ${draftingPlayer.auction_value || 1}</p>
            <div className="price-input-group">
              <label>Actual Price:</label>
              <input
                type="number"
                value={actualPrice}
                onChange={(e) => setActualPrice(e.target.value)}
                min="1"
                max="200"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === 'Enter') confirmDraft();
                  if (e.key === 'Escape') cancelDraft();
                }}
              />
            </div>
            <div className="modal-buttons">
              <button className="btn btn-primary" onClick={confirmDraft}>
                Confirm (${actualPrice || 1})
              </button>
              <button className="btn btn-secondary" onClick={cancelDraft}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};