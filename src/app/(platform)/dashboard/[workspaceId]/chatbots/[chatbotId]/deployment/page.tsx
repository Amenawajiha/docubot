'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { fetchApi } from '@/lib/api';
import { 
  Plus, 
  Trash2, 
  Save, 
  Globe, 
  Copy, 
  Check, 
  Sliders, 
  Code, 
  Terminal, 
  ExternalLink,
  Bot,
  Settings,
  AlertCircle
} from 'lucide-react';

interface WidgetChannelConfig {
  allowed_domains: string[];
  theme: string;
  position: string;
  z_index: number;
}

interface Channel {
  id: string;
  chatbot_id: string;
  workspace_id: string;
  channel_type: string;
  channel_name: string;
  config: WidgetChannelConfig;
  allowed_domains: string[];
}

export default function DashboardPage() {
  const params = useParams();
  const workspaceId = params?.workspaceId as string || 'default-workspace';
  const chatbotId = params?.chatbotId as string || 'default-chatbot';
  const apiEndpoint = `/workspaces/${workspaceId}/chatbots/${chatbotId}/channels`;

  const [channels, setChannels] = useState<Channel[]>([]);
  const [selectedChannel, setSelectedChannel] = useState<Channel | null>(null);
  const [loading, setLoading] = useState(true);

  // Edit states
  const [editName, setEditName] = useState('');
  const [editDomains, setEditDomains] = useState('');
  const [editTheme, setEditTheme] = useState('light');
  const [editPosition, setEditPosition] = useState('bottom-right');
  const [editZIndex, setEditZIndex] = useState(9999);
  const [embedData, setEmbedData] = useState<{ embed_script: string, embed_div: string, widget_url: string } | null>(null);

  // Create state
  const [isCreating, setIsCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDomains, setNewDomains] = useState('localhost:3000');

  // Copy feedbacks
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  // Select channel function
  const selectChannel = useCallback(async (channel: Channel) => {
    setSelectedChannel(channel);
    setEditName(channel.channel_name);
    setEditDomains(channel.allowed_domains ? channel.allowed_domains.join(', ') : '');
    setEditTheme(channel.config?.theme || 'light');
    setEditPosition(channel.config?.position || 'bottom-right');
    setEditZIndex(channel.config?.z_index || 9999);
    setSaveStatus('idle');
    setEmbedData(null);

    try {
      const res = await fetchApi(`${apiEndpoint}/${channel.id}/embed`);
      if (res.ok) {
        const data = await res.json();
        setEmbedData(data);
      }
    } catch (err) {
      console.error('Failed to fetch embed snippet', err);
    }
  }, [apiEndpoint]);

  // Fetch channels function
  const fetchChannels = useCallback(async (selectId?: string) => {
    try {
      const response = await fetchApi(apiEndpoint);
      if (response.ok) {
        const data = await response.json();
        setChannels(data);
        if (data.length > 0) {
          const toSelect = selectId ? data.find((c: Channel) => c.id === selectId) : data[0];
          selectChannel(toSelect || data[0]);
        } else {
          setSelectedChannel(null);
        }
      }
    } catch (err) {
      console.error('Error fetching channels:', err);
    } finally {
      setLoading(false);
    }
  }, [apiEndpoint, selectChannel]);

  useEffect(() => {
    fetchChannels();
  }, [fetchChannels]);

  const handleCreateChannel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;

    try {
      const domainsArray = newDomains.split(',').map(d => d.trim()).filter(Boolean);
      const response = await fetchApi(apiEndpoint, {
        method: 'POST',
        body: JSON.stringify({
          channel_type: 'widget',
          channel_name: newName,
          allowed_domains: domainsArray,
          config: {
            theme: 'light',
            position: 'bottom-right',
            z_index: 9999
          }
        })
      });

      if (response.ok) {
        const created = await response.json();
        setNewName('');
        setNewDomains('localhost:3000');
        setIsCreating(false);
        await fetchChannels(created.id);
      }
    } catch (err) {
      console.error('Error creating channel:', err);
    }
  };

  const handleUpdateChannel = async () => {
    if (!selectedChannel) return;
    setSaveStatus('saving');

    try {
      const domainsArray = editDomains.split(',').map(d => d.trim()).filter(Boolean);
      const response = await fetchApi(`${apiEndpoint}/${selectedChannel.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          channel_name: editName,
          allowed_domains: domainsArray,
          config: {
            theme: editTheme,
            position: editPosition,
            z_index: Number(editZIndex)
          }
        })
      });

      if (response.ok) {
        setSaveStatus('saved');
        setTimeout(() => setSaveStatus('idle'), 3000);
        await fetchChannels(selectedChannel.id);
      } else {
        setSaveStatus('error');
      }
    } catch (err) {
      console.error('Error updating channel:', err);
      setSaveStatus('error');
    }
  };

  const handleDeleteChannel = async (channelId: string) => {
    if (!confirm('Are you sure you want to delete this channel? Any embedded widgets using this channel ID will stop working.')) return;

    try {
      const response = await fetchApi(`${apiEndpoint}/${channelId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await fetchChannels();
      }
    } catch (err) {
      console.error('Error deleting channel:', err);
    }
  };

  const triggerCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const getDeclarativeSnippet = () => {
    if (!embedData) return 'Loading snippet...';
    return `${embedData.embed_div}\n\n${embedData.embed_script}`;
  };

  const getProgrammaticSnippet = () => {
    if (!embedData) return 'Loading snippet...';
    return `<!-- 1. Load the script asynchronously -->\n${embedData.embed_script}\n
<!-- 2. Initialize programmatically -->
<script>
  window.addEventListener('load', function() {
    if (window.DocuBot) {
      window.DocuBot.init({
        chatbotId: "${selectedChannel?.chatbot_id}",
        channelId: "${selectedChannel?.id}",
        theme: "${editTheme}",
        position: "${editPosition}",
        zIndex: ${editZIndex}
      });
    }
  });
</script>`;
  };


  return (
    <div className="flex-1 flex flex-col font-sans bg-slate-50">
      
      {/* Top Header Navigation */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-100 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center space-x-3">
          <div className="bg-gradient-to-br from-blue-600 to-indigo-600 p-2.5 rounded-xl text-white shadow-md shadow-blue-500/20">
            <Bot size={22} className="stroke-[2.2]" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight font-display text-slate-900">DocuBot <span className="text-xs font-semibold px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full ml-1 border border-blue-100">Portal</span></h1>
            <p className="text-[11px] text-slate-500 leading-none">Security Origin Whitelisting Engine</p>
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          <Link 
            href="/demo" 
            className="inline-flex items-center space-x-1.5 px-4 py-2 text-sm font-semibold rounded-xl bg-slate-100 text-slate-700 hover:bg-slate-200 transition-all duration-200"
          >
            <span>Demo Sandbox</span>
            <ExternalLink size={14} />
          </Link>
        </div>
      </header>

      {/* Main Grid Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Channel list (cols 4) */}
        <div className="lg:col-span-4 flex flex-col space-y-6">
          
          <div className="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-md font-bold text-slate-950 font-display">Active Channels</h2>
                <p className="text-xs text-slate-500">Select or add widget deployments</p>
              </div>
              
              {!isCreating && (
                <button
                  onClick={() => setIsCreating(true)}
                  className="p-2 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 transition-all duration-200"
                  aria-label="Add Channel"
                >
                  <Plus size={18} />
                </button>
              )}
            </div>

            {/* Create Channel Inline Form */}
            {isCreating && (
              <form onSubmit={handleCreateChannel} className="bg-slate-50 rounded-xl border border-slate-100 p-4 space-y-3 animate-fade-in">
                <h3 className="text-xs font-semibold text-slate-600 uppercase tracking-wider">New Widget Deployment</h3>
                
                <div>
                  <label className="block text-[11px] font-semibold text-slate-500 mb-1">Name</label>
                  <input
                    type="text"
                    required
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Visa Support Widget"
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-semibold text-slate-500 mb-1">Allowed Domains (comma-separated)</label>
                  <input
                    type="text"
                    value={newDomains}
                    onChange={(e) => setNewDomains(e.target.value)}
                    placeholder="e.g. localhost:3000, site.com"
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                  />
                </div>

                <div className="flex items-center justify-end space-x-2 pt-1">
                  <button
                    type="button"
                    onClick={() => setIsCreating(false)}
                    className="px-3 py-1.5 text-[11px] font-semibold text-slate-500 rounded-lg hover:bg-slate-200 transition-all"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-3 py-1.5 text-[11px] font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-all shadow-sm shadow-blue-500/20"
                  >
                    Create
                  </button>
                </div>
              </form>
            )}

            {/* Channels List */}
            {loading ? (
              <div className="py-8 text-center text-xs text-slate-400">Loading channels...</div>
            ) : channels.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-400">No channels found. Add one to get started!</div>
            ) : (
              <div className="space-y-2">
                {channels.map((chan) => {
                  const isSelected = selectedChannel?.id === chan.id;
                  return (
                    <div
                      key={chan.id}
                      onClick={() => selectChannel(chan)}
                      className={`group w-full text-left p-3.5 rounded-xl border cursor-pointer transition-all duration-200 flex items-center justify-between ${
                        isSelected 
                          ? 'border-blue-600 bg-blue-50/50 shadow-sm shadow-blue-500/5' 
                          : 'border-slate-100 hover:border-slate-300 hover:bg-slate-50 bg-white'
                      }`}
                    >
                      <div className="space-y-1">
                        <h3 className={`text-sm font-semibold tracking-tight ${isSelected ? 'text-blue-600' : 'text-slate-900'}`}>{chan.channel_name}</h3>
                        <div className="flex items-center space-x-1.5 text-[10px] text-slate-500">
                          <Globe size={10} />
                          <span className="truncate max-w-[180px]">
                            {chan.config.allowed_domains.slice(0, 2).join(', ')}
                            {chan.config.allowed_domains.length > 2 && '...'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Delete Action button inside list */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteChannel(chan.id);
                        }}
                        className={`p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-all ${
                          isSelected ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                        }`}
                        aria-label="Delete channel"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}

          </div>

        </div>

        {/* Right Side: Configuration and Embed Code (cols 8) */}
        <div className="lg:col-span-8 flex flex-col space-y-6">
          {selectedChannel ? (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden flex flex-col">
              
              {/* Header Info */}
              <div className="px-6 py-5 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Deployment Config</span>
                  <h2 className="text-lg font-bold text-slate-950 font-display mt-0.5">{selectedChannel.channel_name}</h2>
                  <p className="text-xs text-slate-500 font-mono mt-1">Channel ID: {selectedChannel.id}</p>
                </div>
                
                {/* Save button */}
                <div className="flex items-center space-x-3 shrink-0">
                  {saveStatus === 'saved' && (
                    <span className="text-xs font-semibold text-emerald-600 flex items-center space-x-1">
                      <Check size={14} />
                      <span>Config Saved</span>
                    </span>
                  )}
                  {saveStatus === 'error' && (
                    <span className="text-xs font-semibold text-rose-600 flex items-center space-x-1">
                      <AlertCircle size={14} />
                      <span>Failed to Save</span>
                    </span>
                  )}
                  <button
                    onClick={handleUpdateChannel}
                    disabled={saveStatus === 'saving'}
                    className="inline-flex items-center space-x-1.5 px-4.5 py-2 text-sm font-semibold rounded-xl bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 transition-all shadow-sm shadow-blue-500/20"
                  >
                    <Save size={15} />
                    <span>{saveStatus === 'saving' ? 'Saving...' : 'Save Settings'}</span>
                  </button>
                </div>
              </div>

              {/* Form customizer details */}
              <div className="p-6 md:p-8 space-y-8">
                
                {/* Section 1: Settings */}
                <div className="space-y-5">
                  <h3 className="text-sm font-bold tracking-tight text-slate-900 flex items-center space-x-2 font-display">
                    <Sliders size={16} className="text-blue-600" />
                    <span>Domain Whitelist & Details</span>
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1.5">Deployment Name</label>
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1.5">Whitelisted Domains (comma-separated)</label>
                      <input
                        type="text"
                        value={editDomains}
                        onChange={(e) => setEditDomains(e.target.value)}
                        placeholder="localhost:3000, shop.example.com"
                        className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800"
                      />
                      <span className="text-[10px] text-slate-400 mt-1 block">Only requests originating from these domains will be authorized.</span>
                    </div>
                  </div>
                </div>

                <hr className="border-slate-100" />

                {/* Section 2: Style Tweak */}
                <div className="space-y-5">
                  <h3 className="text-sm font-bold tracking-tight text-slate-900 flex items-center space-x-2 font-display">
                    <Settings size={16} className="text-blue-600" />
                    <span>Widget Appearance Defaults</span>
                  </h3>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-2">Color Theme</label>
                      <div className="flex bg-slate-100 p-1 rounded-xl">
                        {['light', 'dark', 'auto'].map((t) => (
                          <button
                            key={t}
                            type="button"
                            onClick={() => setEditTheme(t)}
                            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg capitalize transition-all ${
                              editTheme === t 
                                ? 'bg-white text-slate-900 shadow-sm' 
                                : 'text-slate-500 hover:text-slate-800'
                            }`}
                          >
                            {t}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-2">Launcher Position</label>
                      <div className="flex bg-slate-100 p-1 rounded-xl">
                        {['bottom-right', 'bottom-left'].map((pos) => (
                          <button
                            key={pos}
                            type="button"
                            onClick={() => setEditPosition(pos)}
                            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                              editPosition === pos 
                                ? 'bg-white text-slate-900 shadow-sm' 
                                : 'text-slate-500 hover:text-slate-800'
                            }`}
                          >
                            {pos === 'bottom-right' ? 'Right' : 'Left'}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1.5">Stacking Index (Z-Index)</label>
                      <input
                        type="number"
                        value={editZIndex}
                        onChange={(e) => setEditZIndex(Number(e.target.value))}
                        className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all text-slate-800"
                      />
                    </div>
                  </div>
                </div>

                <hr className="border-slate-100" />

                {/* Section 3: Embed Snippet Codes */}
                <div className="space-y-6">
                  <div className="flex items-center space-x-2">
                    <Code size={16} className="text-blue-600" />
                    <h3 className="text-sm font-bold tracking-tight text-slate-900 font-display">HTML Integration Snippets</h3>
                  </div>

                  <div className="space-y-6">
                    
                    {/* Variation 1: Declarative */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">Variation 1: Declarative (DOM-based)</h4>
                          <p className="text-[11px] text-slate-500 mt-0.5">Simply paste this anchor div and the async script anywhere on your site.</p>
                        </div>
                        <button
                          onClick={() => triggerCopy(getDeclarativeSnippet(), 'decl')}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 hover:bg-slate-50 transition-all text-slate-600"
                        >
                          {copiedIndex === 'decl' ? (
                            <>
                              <Check size={12} className="text-emerald-500" />
                              <span className="text-emerald-600">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy size={12} />
                              <span>Copy Code</span>
                            </>
                          )}
                        </button>
                      </div>

                      <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-950 p-4">
                        <pre className="text-[11px] text-slate-300 font-mono overflow-x-auto whitespace-pre">
                          {getDeclarativeSnippet()}
                        </pre>
                      </div>
                    </div>

                    {/* Variation 2: Programmatic */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wide">Variation 2: Programmatic (JS-based)</h4>
                          <p className="text-[11px] text-slate-500 mt-0.5">For single-page apps (React/Vue/Next.js) or dynamic initialization triggers.</p>
                        </div>
                        <button
                          onClick={() => triggerCopy(getProgrammaticSnippet(), 'prog')}
                          className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-lg text-xs font-semibold border border-slate-200 hover:bg-slate-50 transition-all text-slate-600"
                        >
                          {copiedIndex === 'prog' ? (
                            <>
                              <Check size={12} className="text-emerald-500" />
                              <span className="text-emerald-600">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy size={12} />
                              <span>Copy Code</span>
                            </>
                          )}
                        </button>
                      </div>

                      <div className="relative rounded-xl overflow-hidden border border-slate-200 bg-slate-950 p-4">
                        <pre className="text-[11px] text-slate-300 font-mono overflow-x-auto whitespace-pre">
                          {getProgrammaticSnippet()}
                        </pre>
                      </div>
                    </div>

                  </div>
                </div>

              </div>

            </div>
          ) : (
            <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-12 text-center flex flex-col items-center justify-center space-y-3">
              <Terminal size={36} className="text-slate-300" />
              <h2 className="text-md font-bold text-slate-900">No Channel Selected</h2>
              <p className="text-xs text-slate-500 max-w-sm">Please create a channel or select an existing widget channel from the list on the left to start configuring deployments.</p>
            </div>
          )}
        </div>

      </main>
    </div>
  );
}
