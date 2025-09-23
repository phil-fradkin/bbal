import React from 'react';

interface StatCellProps {
  value: number | string;
  zScore?: number;
  isNegativeCategory?: boolean;
  isPercentage?: boolean;
}

export const StatCell: React.FC<StatCellProps> = ({
  value,
  zScore,
  isNegativeCategory = false,
  isPercentage = false
}) => {
  if (value === undefined || value === null) {
    return <span>-</span>;
  }

  // For negative categories like turnovers, invert the color logic
  const adjustedZScore = isNegativeCategory && zScore ? -zScore : zScore;

  // Determine color class based on z-score strength (with subtle opacity)
  let colorClass = '';
  if (adjustedZScore !== undefined) {
    if (adjustedZScore >= 2.0) {
      colorClass = 'stat-elite'; // Elite (subtle dark green)
    } else if (adjustedZScore >= 1.0) {
      colorClass = 'stat-excellent'; // Excellent (subtle green)
    } else if (adjustedZScore >= 0.5) {
      colorClass = 'stat-good'; // Good (subtle light green)
    } else if (adjustedZScore >= 0) {
      colorClass = 'stat-above'; // Above average (very subtle green)
    } else if (adjustedZScore >= -0.5) {
      colorClass = 'stat-below'; // Below average (very subtle red)
    } else if (adjustedZScore >= -1.0) {
      colorClass = 'stat-poor'; // Poor (subtle light red)
    } else {
      colorClass = 'stat-terrible'; // Terrible (subtle red)
    }
  }

  const displayValue = isPercentage ? `${value}%` : value;

  return (
    <span
      className={`stat-cell ${colorClass}`}
      title={zScore !== undefined ? `Z-Score: ${zScore.toFixed(2)}` : undefined}
    >
      {displayValue}
    </span>
  );
};