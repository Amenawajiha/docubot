(function () {
  // Prevent duplicate load
  if (window.DocuBotInitialized) return;
  window.DocuBotInitialized = true;

  // Extract backend URL dynamically from the script source URL
  let BACKEND_URL = 'http://localhost:3000';
  if (typeof document !== 'undefined') {
    const currentScript = document.currentScript || document.querySelector('script[src*="/widget.js"]');
    if (currentScript && currentScript.src) {
      try {
        const url = new URL(currentScript.src);
        BACKEND_URL = url.origin;
        // Optionally read data attributes directly from script if declarative
        window._docubotScriptData = {
          chatbotId: currentScript.getAttribute('data-chatbot-id'),
          workspace: currentScript.getAttribute('data-workspace'),
          channelId: currentScript.getAttribute('data-channel') || currentScript.getAttribute('data-channel-id')
        };
      } catch (e) {
        console.warn('DocuBot: Could not parse backend URL from script source, using default.', e);
      }
    }
  }

  // Helper to generate UUID for session
  function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  // Get or create session ID in sessionStorage
  function getSessionId() {
    let sessionId = sessionStorage.getItem('docubot_chat_session_id');
    if (!sessionId) {
      sessionId = generateUUID();
      sessionStorage.setItem('docubot_chat_session_id', sessionId);
    }
    return sessionId;
  }

  // Inject styles into the parent page
  function injectStyles(config) {
    const styleId = 'docubot-widget-styles';
    if (document.getElementById(styleId)) return;

    const style = document.createElement('style');
    style.id = styleId;
    style.innerHTML = `
      .docubot-launcher {
        position: fixed;
        bottom: 24px;
        right: 24px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
        box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4);
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        z-index: ${config.zIndex || 9999};
        border: 2px solid #FFFFFF;
      }
      .docubot-launcher:hover {
        transform: scale(1.08) translateY(-2px);
        box-shadow: 0 6px 24px rgba(37, 99, 235, 0.5);
      }
      .docubot-launcher:active {
        transform: scale(0.95);
      }
      .docubot-launcher svg {
        width: 26px;
        height: 26px;
        fill: none;
        stroke: #FFFFFF;
        stroke-width: 2.2;
        stroke-linecap: round;
        stroke-linejoin: round;
        transition: transform 0.4s ease;
      }
      .docubot-launcher.open svg {
        transform: rotate(90deg);
      }
      .docubot-iframe-container {
        position: fixed;
        bottom: 96px;
        right: 24px;
        width: 400px;
        height: 600px;
        max-height: calc(100vh - 120px);
        max-width: calc(100vw - 48px);
        background: #FFFFFF;
        border-radius: 16px;
        box-shadow: 0 12px 40px rgba(15, 23, 42, 0.16);
        border: 1px solid rgba(37, 99, 235, 0.15);
        overflow: hidden;
        z-index: ${config.zIndex || 9999};
        opacity: 0;
        transform: translateY(20px) scale(0.95);
        pointer-events: none;
        transition: opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1), transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      }
      .docubot-iframe-container.open {
        opacity: 1;
        transform: translateY(0) scale(1);
        pointer-events: all;
      }
      @media (max-width: 480px) {
        .docubot-iframe-container {
          bottom: 0;
          right: 0;
          width: 100vw;
          height: 100vh;
          max-height: 100vh;
          max-width: 100vw;
          border-radius: 0;
        }
      }
      
      /* Left aligned styling */
      .docubot-launcher.launcher-left {
        left: 24px;
        right: auto;
      }
      .docubot-iframe-container.iframe-left {
        left: 24px;
        right: auto;
      }
    `;
    document.head.appendChild(style);
  }

  // Initialize the Widget Instance
  async function initializeWidget(options) {
    const channelId = options.channelId;
    if (!channelId) {
      console.error('DocuBot: channelId is required for initialization.');
      return;
    }

    // 1. Fetch Configuration from Backend
    let config = {
      allowed_domains: [],
      theme: 'light',
      position: 'bottom-right',
      zIndex: 9999
    };

    try {
      const response = await fetch(`${BACKEND_URL}/api/channels/${channelId}/config`);
      if (response.ok) {
        const backendConfig = await response.json();
        config = { ...config, ...backendConfig };
      } else {
        console.warn('DocuBot: Failed to fetch channel config. Using defaults.');
      }
    } catch (e) {
      console.warn('DocuBot: Error fetching config, using defaults.', e);
    }

    // Merge options (programmatic configs override backend config)
    const mergedConfig = {
      chatbotId: options.chatbotId || window._docubotScriptData?.chatbotId || '',
      workspace: options.workspace || window._docubotScriptData?.workspace || '',
      channelId: channelId,
      theme: options.theme || config.theme || 'light',
      position: options.position || config.position || 'bottom-right',
      zIndex: options.zIndex || config.z_index || 9999,
      simulatedOrigin: options.simulatedOrigin || ''
    };

    injectStyles(mergedConfig);

    // Create wrapper/anchor if not exists
    let wrapper = document.getElementById('docubot-chat-widget-root');
    if (!wrapper) {
      wrapper = document.createElement('div');
      wrapper.id = 'docubot-chat-widget-root';
      document.body.appendChild(wrapper);
    }

    // Create Floating Launcher Button
    const launcher = document.createElement('div');
    launcher.className = `docubot-launcher ${mergedConfig.position === 'bottom-left' ? 'launcher-left' : ''}`;
    
    // Bubble Chat Icon SVG
    const chatIcon = `
      <svg id="docubot-icon-chat" viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
      </svg>
    `;
    // Close Icon SVG
    const closeIcon = `
      <svg id="docubot-icon-close" viewBox="0 0 24 24" style="display:none;">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    `;
    launcher.innerHTML = chatIcon + closeIcon;
    wrapper.appendChild(launcher);

    // Create Iframe Container
    const container = document.createElement('div');
    container.className = `docubot-iframe-container ${mergedConfig.position === 'bottom-left' ? 'iframe-left' : ''}`;
    
    const sessionId = getSessionId();
    
    // Build Iframe Source URL passing configurations
    const targetOrigin = mergedConfig.simulatedOrigin || window.location.origin;
    
    // The widget script might be served by the backend or frontend. 
    // We need the iframe to point to the Next.js frontend.
    // If BACKEND_URL contains the backend port (e.g. 8001), swap to frontend port (3000).
    const frontendUrl = BACKEND_URL.includes('8001') ? BACKEND_URL.replace('8001', '3000') : BACKEND_URL;
    
    const iframeUrl = `${frontendUrl}/widget/chat/${mergedConfig.channelId}?session_id=${sessionId}&theme=${mergedConfig.theme}&origin=${encodeURIComponent(targetOrigin)}&workspace=${mergedConfig.workspace}&chatbot=${mergedConfig.chatbotId}`;

    const iframe = document.createElement('iframe');
    iframe.src = iframeUrl;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.style.background = 'transparent';
    iframe.setAttribute('allow', 'clipboard-write');

    container.appendChild(iframe);
    wrapper.appendChild(container);

    let isOpen = false;

    // Toggle logic
    function toggleChat() {
      isOpen = !isOpen;
      const chatSvg = document.getElementById('docubot-icon-chat');
      const closeSvg = document.getElementById('docubot-icon-close');

      if (isOpen) {
        launcher.classList.add('open');
        container.classList.add('open');
        if (chatSvg) chatSvg.style.display = 'none';
        if (closeSvg) closeSvg.style.display = 'block';
        // Post a message to iframe to focus input or refresh state
        iframe.contentWindow.postMessage({ type: 'docubot-open' }, '*');
      } else {
        launcher.classList.remove('open');
        container.classList.remove('open');
        if (chatSvg) chatSvg.style.display = 'block';
        if (closeSvg) closeSvg.style.display = 'none';
      }
    }

    launcher.addEventListener('click', toggleChat);

    // Listen for events from the iframe (e.g. close requests)
    window.addEventListener('message', function (event) {
      if (event.data && event.data.type === 'docubot-close') {
        if (isOpen) toggleChat();
      }
    });
  }

  // --- Variation 1: Declarative (DOM-based) Initialization ---
  function checkDeclarative() {
    const anchor = document.getElementById('docubot-chat-widget');
    if (anchor) {
      const chatbotId = anchor.getAttribute('data-chatbot-id') || window._docubotScriptData?.chatbotId || '';
      const workspace = anchor.getAttribute('data-workspace') || window._docubotScriptData?.workspace || '';
      const channelId = anchor.getAttribute('data-channel-id') || window._docubotScriptData?.channelId || '';
      const simulatedOrigin = anchor.getAttribute('data-simulated-origin') || '';
      if (channelId) {
        initializeWidget({ chatbotId, workspace, channelId, simulatedOrigin });
      }
    } else if (window._docubotScriptData && window._docubotScriptData.channelId) {
      // Initialize from script tag data attributes
      initializeWidget({
        chatbotId: window._docubotScriptData.chatbotId,
        workspace: window._docubotScriptData.workspace,
        channelId: window._docubotScriptData.channelId
      });
    }
  }

  // Run immediately or on load
  if (document.readyState === 'complete' || document.readyState === 'interactive') {
    checkDeclarative();
  } else {
    document.addEventListener('DOMContentLoaded', checkDeclarative);
  }

  // --- Variation 2: Programmatic (JS-based) Initialization ---
  window.DocuBot = {
    init: function (config) {
      initializeWidget(config);
    }
  };
})();
