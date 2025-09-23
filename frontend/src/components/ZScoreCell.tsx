import React from 'react';

interface ZScoreCellProps {
  value: number | undefined;
  isNegativeCategory?: boolean;
}

export const ZScoreCell: React.FC<ZScoreCellProps> = ({ value, isNegativeCategory = false }) => {
  if (value === undefined || value === null) {
    return <span>-</span>;
  }

  // For negative categories like turnovers, invert the color logic
  const adjustedValue = isNegativeCategory ? -value : value;

  // Determine color based on z-score strength
  let colorClass = '';
  if (adjustedValue >= 2.0) {
    colorClass = 'z-elite'; // Elite (dark green)
  } else if (adjustedValue >= 1.0) {
    colorClass = 'z-excellent'; // Excellent (green)
  } else if (adjustedValue >= 0.5) {
    colorClass = 'z-good'; // Good (light green)
  } else if (adjustedValue >= 0) {
    colorClass = 'z-above'; // Above average (pale green)
  } else if (adjustedValue >= -0.5) {
    colorClass = 'z-below'; // Below average (pale red)
  } else if (adjustedValue >= -1.0) {
    colorClass = 'z-poor'; // Poor (light red)
  } else {
    colorClass = 'z-terrible'; // Terrible (red)
  }

  return (
    <span
      className={`z-score-cell ${colorClass}`}
      title={`Z-Score: ${value.toFixed(2)}`}
    >
      {value.toFixed(2)}
    </span>
  );
};