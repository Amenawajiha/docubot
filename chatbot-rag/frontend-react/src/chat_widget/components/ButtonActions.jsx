import React from 'react';
import './ButtonActions.css';

const ButtonActions = ({ buttons, onButtonClick, disabled = false }) => {
  if (!buttons || buttons.length === 0) {
    return null;
  }

  return (
    <div className="quick-actions">
      {buttons.map((button, index) => (
        <button
          key={index}
          className="quick-action"
          onClick={() => onButtonClick(button.action)}
          disabled={disabled}
        >
          {button.label}
        </button>
      ))}
    </div>
  );
};

export default ButtonActions;