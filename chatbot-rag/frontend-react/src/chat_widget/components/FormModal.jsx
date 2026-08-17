import React, { useState, useEffect } from 'react';
import './FormModal.css';

const FormModal = ({ 
  isOpen, 
  onClose, 
  onSubmit, 
  title, 
  fields, 
  submitLabel = 'Submit',
  initialData = {}
}) => {
  const [formValues, setFormValues] = useState({});
  const [errors, setErrors] = useState({});

  useEffect(() => {
    if (isOpen) {
      // Initialize form with initial data or empty values
      const initialValues = {};
      fields.forEach(field => {
        initialValues[field.name] = initialData[field.name] || '';
      });
      setFormValues(initialValues);
      setErrors({});
    }
  }, [isOpen]);

  const handleChange = (fieldName, value) => {
    setFormValues(prev => ({
      ...prev,
      [fieldName]: value
    }));
    // Clear error for this field when user starts typing
    if (errors[fieldName]) {
      setErrors(prev => ({
        ...prev,
        [fieldName]: null
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    let isValid = true;

    fields.forEach(field => {
      if (field.required && (!formValues[field.name] || formValues[field.name].trim() === '')) {
        newErrors[field.name] = `${field.label} is required`;
        isValid = false;
      }
    });

    setErrors(newErrors);
    return isValid;
  };

  const handleSubmit = () => {
    if (validateForm()) {
      onSubmit(formValues);
      setFormValues({});
      setErrors({});
    }
  };

  const handleOverlayClick = (e) => {
    if (e.target.classList.contains('modal-overlay')) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay active" onClick={handleOverlayClick}>
      <div className="modal">
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="modal-close" onClick={onClose}>
            <i className="fas fa-times"></i>
          </button>
        </div>
        
        <div className="modal-body">
          {fields.map((field) => (
            <div key={field.name} className="form-group">
              <label htmlFor={field.name}>
                {field.label}
                {field.required && <span style={{ color: 'var(--danger)' }}> *</span>}
              </label>
              
              {field.type === 'select' ? (
                <select
                  id={field.name}
                  value={formValues[field.name] || ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  className={errors[field.name] ? 'error' : ''}
                >
                  <option value="">Select {field.label}</option>
                  {field.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : field.type === 'textarea' ? (
                <textarea
                  id={field.name}
                  value={formValues[field.name] || ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  placeholder={field.placeholder || ''}
                  rows={field.rows || 3}
                  className={errors[field.name] ? 'error' : ''}
                />
              ) : (
                <input
                  type={field.type}
                  id={field.name}
                  value={formValues[field.name] || ''}
                  onChange={(e) => handleChange(field.name, e.target.value)}
                  placeholder={field.placeholder || ''}
                  min={field.type === 'date' || field.type === 'datetime-local' ? new Date().toISOString().split('T')[0] : undefined}
                  className={errors[field.name] ? 'error' : ''}
                />
              )}
              
              {errors[field.name] && (
                <span className="error-message">{errors[field.name]}</span>
              )}
            </div>
          ))}
        </div>
        
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSubmit}>
            <i className="fas fa-check"></i> {submitLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FormModal;