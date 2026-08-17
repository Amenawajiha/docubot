import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import ReactMarkdown from 'react-markdown';
import flowManager from './utils/flowManager';
import { flows } from './flows';
import ButtonActions from './components/ButtonActions';
import FormModal from './components/FormModal';
import SummaryCard from './components/SummaryCard';
import './ChatWidget.css';
import DOMPurify from 'dompurify';

// Debug mode - set to false for production
const DEBUG = process.env.NODE_ENV === 'development';
const debugLog = (...args) => {
  if (DEBUG) console.log(...args);
};

const ChatWidget = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [userId, setUserId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Flow system state
  const [showModal, setShowModal] = useState(false);
  const [currentModalFlow, setCurrentModalFlow] = useState(null);
  const [isProcessingFlow, setIsProcessingFlow] = useState(false);
  
  const ws = useRef(null);
  const messagesStartRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Initialize User ID
  useEffect(() => {
    let storedUserId = localStorage.getItem('chat_user_id');
    if (!storedUserId) {
      storedUserId = `user_${uuidv4().slice(0, 8)}`;
      localStorage.setItem('chat_user_id', storedUserId);
    }
    setUserId(storedUserId);

  }, []);

  // Initialize WebSocket
  useEffect(() => {
    if (!userId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${window.location.host}/ws?user_id=${userId}`;
    
    debugLog('Connecting to WebSocket:', wsUrl);  // Debug log
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      debugLog('Connected to WebSocket');
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      let response;
      try {
        response = JSON.parse(event.data);
      } catch {
        console.error("Invalid WebSocket message received:", event.data);
        return;
      }
      setIsLoading(false);
      
      const newMessage = {
        role: 'assistant',
        content: response.content,
        type: response.type || 'answer',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      
      setMessages(prev => [...prev, newMessage]);
    };

    ws.current.onclose = (event) => {
      console.log('WebSocket Disconnected:', event.code, event.reason);
      setIsConnected(false);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket Error:', error);
      setIsConnected(false);
      setIsLoading(false);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [userId]);


  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // To handle scroll visibility
  useEffect(() => {
    const messagesDiv = messagesEndRef.current?.parentElement;
    if (!messagesDiv) return;

    const handleScroll = () => {
      const scrollTop = messagesDiv.scrollTop;
      setShowScrollButton(scrollTop > 200);
    };

    messagesDiv.addEventListener('scroll', handleScroll);
    return () => messagesDiv.removeEventListener('scroll', handleScroll);
  }, []);

  // Show greeting on mount
  useEffect(() => {
    if (!flowManager.isGreetingShown()) {
      setTimeout(() => {
        handleFlowAction('greeting');
      }, 1000);
    }
  }, []);

  const sendMessageToBackend = (message) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'store_message',
        message: message
      }));
    }
  };

  const handleFormSubmit = (formData) => {
    
    const sanitizedFormData = Object.fromEntries(
      Object.entries(formData).map(([key, value]) => [
        key,
        DOMPurify.sanitize(String(value))
      ])
    );

    // Create form submission message
    const formSummary = Object.entries(sanitizedFormData)
      .map(([key, value]) => {
        const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        return `${label}: ${value}`;
      })
      .join(', ');

    const formMessage = {
      content: `[Form Submission] ${formSummary}`,
      role: "user",
      timestamp: new Date().toISOString(),
      user_id: userId,
      metadata: {
        interaction_type: "form_submission",
        form_data: sanitizedFormData,
      }
    };

    // Send to backend for storage
    sendMessageToBackend(formMessage);

    // Save form data
    flowManager.saveFormData(sanitizedFormData);    
    flowManager.markFormSubmitted();
    flowManager.addToHistory('form_submit', { data: sanitizedFormData });
    
    // Close modal
    setShowModal(false);
    setCurrentModalFlow(null);

    // Show typing indicator
    setIsLoading(true);

    // Show confirmation message
    setTimeout(() => {
      setIsLoading(false);
      // Get next action from flow
      const currentFlowKey = flowManager.currentFlow;
      
      const flow = flows[currentFlowKey];
      
      if (flow && flow.nextAction) {
        handleFlowAction(flow.nextAction);
      } 
    }, 800);
  };

  const handleFlowAction = (flowKey) => {
    
    if (isProcessingFlow) return;
    
    const flow = flows[flowKey];
    if (!flow) {
      console.error('Flow not found for key:', flowKey);
      return;
    }

    // Create button click message
    const buttonMessage = {
      content: `[Button: ${flowKey}]`, 
      role: "user",
      timestamp: new Date().toISOString(),
      user_id: userId,
      metadata: {
        interaction_type: "button_click",
      }
    };

    // Send to backend for storage
    sendMessageToBackend(buttonMessage);

    // Update flow manager state
    flowManager.setCurrentFlow(flowKey);
    
    flowManager.setProcessing(true);
    flowManager.addToHistory('button_click', { action: flowKey });
    
    setIsProcessingFlow(true);

    // Show typing indicator
    setIsLoading(true);

    // Simulate processing delay
    setTimeout(() => {
      setIsLoading(false);

      // Handle different flow types
      if (flow.action === 'showForm') {
        setCurrentModalFlow(flowKey);
        setShowModal(true);
        flowManager.setCurrentFormFlow(flowKey);
      } else if (flow.type === 'summary') {
        const summaryData = flowManager.formatFormDataForSummary();
        addBotMessage(flow.message, flow.buttons, summaryData);
      } else {
        addBotMessage(flow.message, flow.buttons);
      }

      // Mark greeting as shown
      if (flowKey === 'greeting') {
        flowManager.markGreetingShown();
      }

      setIsProcessingFlow(false);
      flowManager.setProcessing(false);
    }, 800);
  };

  const addBotMessage = (content, showButtons = null, showSummary = null) => {
    const botMsg = {
      role: 'assistant',
      content,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      buttons: showButtons,
      summary: showSummary
    };
        
    setMessages(prev => {
      const newMessages = [...prev, botMsg];
      return newMessages;
    });
    
    // Create message for backend storage
    const botMessage = {
      content: content,
      role: "assistant",
      timestamp: new Date().toISOString(),
      user_id: userId,
      metadata: {
        interaction_type: "bot_response",
        // flow_key: flowManager.getCurrentFlow(),
        has_buttons: !!showButtons,
      }
    };

    // Send to backend for storage
    sendMessageToBackend(botMessage);

  };

  const handleModalClose = () => {
    setShowModal(false);
    flowManager.markFormCanceled();
    
    // Show follow-up message
    setTimeout(() => {
      addBotMessage(
        "You closed the form without completing it.",
        [
          { label: '🛂 Visa Services', action: 'visaServices' },
          { label: '📋 Travel Documentation', action: 'travelDocsForVisa' },
          { label: '🏖️ Holiday Packages', action: 'holidayPackages' },
          { label: '📞 Contact Support', action: 'callSupport' }
        ]
      );
    }, 300);
  };

  const handleSendMessage = (e) => {
    if (e) e.preventDefault();
    if (!input.trim() || !isConnected) return;

    const userMsg = { 
      role: 'user', 
      content: input,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);

    // Add to flow history
    flowManager.addToHistory('user_message', { message: input });

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        query: input,
        user_id: userId
      }));
    } else {
      console.error('WebSocket is not open');
      setIsLoading(false);
    }

    setInput('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const scrollToTop = () => {
    messagesStartRef.current?.scrollIntoView({ behavior: 'smooth' });
  };


  return (
    <div className="chat-app">
      {/* Header */}
      <header className="chat-header">
        <div className="header-content">
          <div className="logo">
            <i className="fas fa-plane-departure"></i>
          </div>
          <div className="header-text">
            <h1>SchengenVisaItinerary</h1>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="chat-container">

        {/* Chat Messages */}
        <main className="chat-messages">

          <div ref={messagesStartRef} /> 
          
          {messages.length === 0 && (
            <div className="welcome-screen">
              <div className="welcome-icon">
                <i className="fas fa-robot"></i>
              </div>
              <h2>Welcome to SchengenVisaItinerary</h2>
              <p>Your AI-powered travel assistant for Schengen visa applications, flight bookings, and holiday planning. How can we help you today?</p>
            </div>
          )}
          
          {messages.map((msg, index) => (
            <div key={index}>
              <div className={`message ${msg.role}`}>
                <div className="message-avatar">
                  {msg.role === 'user' ? (
                    <i className="fas fa-user"></i>
                  ) : (
                    <i className="fas fa-robot"></i>
                  )}
                </div>
                <div className="message-content">
                  <div className="message-bubble">
                    {msg.type === 'clarification' && (
                      <div className="msg-label">🤔 Clarification needed:</div>
                    )}
                    {msg.type === 'error' && (
                      <div className="msg-label">❌ Error:</div>
                    )}
                    <div className="message-text">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                    <small className="message-time">{msg.timestamp}</small>
                  </div>
                </div>
              </div>
              
              {/* Show summary if present */}
              {msg.summary && (
                <SummaryCard data={msg.summary} />
              )}
              
              {/* Show buttons if present */}
              {msg.buttons && (
                <ButtonActions 
                  buttons={msg.buttons}
                  onButtonClick={handleFlowAction}
                  disabled={isProcessingFlow}
                />
              )}
            </div>
          ))}
          
          {isLoading && (
            <div className="message bot">
              <div className="message-avatar">
                <i className="fas fa-robot"></i>
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <div className="typing-dot"></div>
                  <span style={{ marginLeft: '8px', fontSize: '0.875rem', color: 'var(--gray-600)' }}>
                    Thinking...
                  </span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        {showScrollButton && (
          <button 
            className="scroll-to-top-btn" 
            onClick={scrollToTop}
            aria-label="Scroll to top"
          >
            <i className="fas fa-arrow-up"></i>
          </button>
        )}
      </div>

      {/* Input Area */}
      <div className="input-area">
        <div className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={isConnected ? "Type your message or choose a service..." : "Connecting..."}
            disabled={!isConnected || isLoading}
            autoComplete="off"
          />
          <div className="input-actions">
            <button 
              onClick={handleSendMessage}
              className="action-btn send-btn" 
              disabled={!input.trim() || !isConnected || isLoading}
            >
              <i className="fas fa-paper-plane"></i>
            </button>
          </div>
        </div>
      </div>

      {/* Modal */}
      {currentModalFlow && (
        <FormModal
          isOpen={showModal}
          onClose={handleModalClose}
          onSubmit={handleFormSubmit}
          title={flows[currentModalFlow]?.message || 'Form'}
          fields={flows[currentModalFlow]?.fields || []}
          submitLabel={flows[currentModalFlow]?.submitLabel || 'Submit'}
          initialData={flowManager.getFormData()}
        />
      )}
    </div>
  );
};

export default ChatWidget;