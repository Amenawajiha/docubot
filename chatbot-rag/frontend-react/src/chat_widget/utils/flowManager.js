// flowManager.js - Manages button flow logic and state

import { flows } from '../flows';

/**
 * FlowManager class to handle all flow-related operations
 */
export class FlowManager {
  constructor() {
    this.currentFlow = 'greeting';
    this.conversationHistory = [];
    this.isProcessing = false;
    this.hasShownGreeting = false;
    this.currentFormFlow = null;
    this.formCanceled = false;
    this.formData = {};
  }

  /**
   * Get a flow by its key
   * @param {string} flowKey - The flow identifier
   * @returns {object|null} The flow object or null if not found
   */
  getFlow(flowKey) {
    return flows[flowKey] || null;
  }

  /**
   * Check if a flow exists
   * @param {string} flowKey - The flow identifier
   * @returns {boolean} True if flow exists
   */
  flowExists(flowKey) {
    return !!flows[flowKey];
  }

  /**
   * Set the current flow
   * @param {string} flowKey - The flow identifier
   */
  setCurrentFlow(flowKey) {
    if (this.flowExists(flowKey)) {
      this.currentFlow = flowKey;
      return true;
    }
    console.error('[FlowManager] Flow does not exist:', flowKey);
    return false;
  }

  /**
   * Get the current flow object
   * @returns {object|null} The current flow object
   */
  getCurrentFlow() {
    return this.getFlow(this.currentFlow);
  }

  /**
   * Save form data
   * @param {object} data - Form data to save
   */
  saveFormData(data) {
    this.formData = { ...this.formData, ...data };
  }

  /**
   * Get all saved form data
   * @returns {object} All saved form data
   */
  getFormData() {
    return this.formData;
  }

  /**
   * Clear all form data
   */
  clearFormData() {
    this.formData = {};
  }

  /**
   * Add interaction to conversation history
   * @param {string} type - Type of interaction ('button', 'form', 'message')
   * @param {object} data - Interaction data
   */
  addToHistory(type, data) {
    this.conversationHistory.push({
      type,
      data,
      timestamp: new Date().toISOString(),
      flow: this.currentFlow
    });
  }

  /**
   * Get conversation history
   * @returns {array} Conversation history
   */
  getHistory() {
    return this.conversationHistory;
  }

  /**
   * Clear conversation history
   */
  clearHistory() {
    this.conversationHistory = [];
  }

  /**
   * Check if processing is in progress
   * @returns {boolean} True if processing
   */
  isFlowProcessing() {
    return this.isProcessing;
  }

  /**
   * Set processing state
   * @param {boolean} state - Processing state
   */
  setProcessing(state) {
    this.isProcessing = state;
  }

  /**
   * Mark greeting as shown
   */
  markGreetingShown() {
    this.hasShownGreeting = true;
  }

  /**
   * Check if greeting has been shown
   * @returns {boolean} True if greeting shown
   */
  isGreetingShown() {
    return this.hasShownGreeting;
  }

  /**
   * Reset the entire flow state
   */
  reset() {
    this.currentFlow = 'greeting';
    this.formData = {};
    this.conversationHistory = [];
    this.isProcessing = false;
    this.hasShownGreeting = false;
    this.currentFormFlow = null;
    this.formCanceled = false;
  }

  /**
   * Set current form flow
   * @param {string} flowKey - The form flow identifier
   */
  setCurrentFormFlow(flowKey) {
    this.currentFormFlow = flowKey;
  }

  /**
   * Get current form flow
   * @returns {string|null} Current form flow key
   */
  getCurrentFormFlow() {
    return this.currentFormFlow;
  }

  /**
   * Mark form as canceled
   */
  markFormCanceled() {
    this.formCanceled = true;
  }

  /**
   * Mark form as submitted
   */
  markFormSubmitted() {
    this.formCanceled = false;
  }

  /**
   * Check if form was canceled
   * @returns {boolean} True if form was canceled
   */
  isFormCanceled() {
    return this.formCanceled;
  }

  /**
   * Validate if flow transition is allowed
   * @param {string} fromFlow - Current flow
   * @param {string} toFlow - Target flow
   * @returns {boolean} True if transition is allowed
   */
  canTransition(fromFlow, toFlow) {
    // Add any validation logic here
    // For now, allow all transitions if target flow exists
    return this.flowExists(toFlow);
  }

  /**
   * Get next action from current flow
   * @returns {string|null} Next action or null
   */
  getNextAction() {
    const flow = this.getCurrentFlow();
    return flow?.nextAction || null;
  }

  /**
   * Check if current flow is a form
   * @returns {boolean} True if current flow is a form
   */
  isCurrentFlowForm() {
    const flow = this.getCurrentFlow();
    return flow?.action === 'showForm';
  }

  /**
   * Check if current flow is a summary
   * @returns {boolean} True if current flow is a summary
   */
  isCurrentFlowSummary() {
    const flow = this.getCurrentFlow();
    return flow?.type === 'summary';
  }

  /**
   * Get flow message
   * @param {string} flowKey - Flow identifier (optional, uses current if not provided)
   * @returns {string|null} Flow message
   */
  getFlowMessage(flowKey = null) {
    const flow = flowKey ? this.getFlow(flowKey) : this.getCurrentFlow();
    return flow?.message || null;
  }

  /**
   * Get flow buttons
   * @param {string} flowKey - Flow identifier (optional, uses current if not provided)
   * @returns {array} Flow buttons
   */
  getFlowButtons(flowKey = null) {
    const flow = flowKey ? this.getFlow(flowKey) : this.getCurrentFlow();
    return flow?.buttons || [];
  }

  /**
   * Get flow fields (for forms)
   * @param {string} flowKey - Flow identifier (optional, uses current if not provided)
   * @returns {array} Flow fields
   */
  getFlowFields(flowKey = null) {
    const flow = flowKey ? this.getFlow(flowKey) : this.getCurrentFlow();
    return flow?.fields || [];
  }

  /**
   * Get flow submit label (for forms)
   * @param {string} flowKey - Flow identifier (optional, uses current if not provided)
   * @returns {string} Submit label
   */
  getFlowSubmitLabel(flowKey = null) {
    const flow = flowKey ? this.getFlow(flowKey) : this.getCurrentFlow();
    return flow?.submitLabel || 'Submit';
  }

  /**
   * Build context for RAG system
   * @returns {object} Context object for RAG
   */
  buildRAGContext() {
    return {
      conversation_type: 'button_flow',
      current_flow: this.currentFlow,
      form_data: this.formData,
      history: this.conversationHistory,
      last_interaction: this.conversationHistory[this.conversationHistory.length - 1] || null
    };
  }

  /**
   * Format form data for display (summary)
   * @returns {object} Formatted form data
   */
  formatFormDataForSummary() {
    const formatted = {};
    Object.entries(this.formData).forEach(([key, value]) => {
      // Only filter out null/undefined, keep empty strings and zeros
      if (value !== null && value !== undefined) {
        const label = key
          .replace(/_/g, ' ')
          .replace(/\b\w/g, l => l.toUpperCase());
        formatted[label] = value;
      } 
    });

    return formatted;
  }
}

// Create a singleton instance
const flowManagerInstance = new FlowManager();

export default flowManagerInstance;