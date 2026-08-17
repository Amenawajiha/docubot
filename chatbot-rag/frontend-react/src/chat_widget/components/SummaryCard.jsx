import React from 'react';
import './SummaryCard.css';

const SummaryCard = ({ data, title = "Summary of Your Request" }) => {
  if (!data || Object.keys(data).length === 0) {
    return null;
  }

  const formatLabel = (key) => {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="summary-card">
      <div className="summary-header">
        <i className="fas fa-check-circle"></i>
        <h4>{title}</h4>
      </div>
      {Object.entries(data).map(([key, value]) => {
        if (value && value !== '') {
          return (
            <div key={key} className="summary-item">
              <label>{formatLabel(key)}:</label>
              <span>{value}</span>
            </div>
          );
        }
        return null;
      })}
    </div>
  );
};

export default SummaryCard;