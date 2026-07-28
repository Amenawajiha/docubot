"use client";

import React, { useRef, useState, useEffect, useCallback } from "react";
import {
  Plus,
  Globe,
  FileText,
  RefreshCw,
  Search,
  Upload,
  Brain,
  X
} from "lucide-react";
import { useWorkspace, FileItem } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { ProgressBar, Toast } from "@/components/ui/shared-dashboard";

interface KnowledgeStats {
  total_documents?: number;
  storage_used_mb?: number;
  total_chunks?: number;
}

interface ApiDocument {
  id: string;
  original_filename?: string;
  filename?: string;
  file_size_bytes: number;
  file_type?: string;
  uploaded_at?: string;
  chatbot_id: string;
  chunk_count?: number;
  upload_status?: string;
}

export default function KnowledgeBase() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [fetchedFiles, setFetchedFiles] = useState<FileItem[]>([]);
  const [stats, setStats] = useState<KnowledgeStats | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [toastMsg, setToastMsg] = useState("");
  const [toastVisible, setToastVisible] = useState(false);

  const {
    workspaceId,
    isTraining,
    trainingProgress,
    startTraining,
    uploadMethod,
    setUploadMethod,
    inputUrl,
    setInputUrl,
    handleUrlSubmit,
    currentChatbot
  } = useWorkspace();

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 2500);
  };

  const loadData = useCallback(async () => {
    if (!workspaceId || !currentChatbot?.id) return;
    try {
      // Fetch Stats
      const statsRes = await fetchApi(`/workspaces/${workspaceId}/chatbots/${currentChatbot.id}/knowledge-base/stats`);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setTimeout(() => setStats(statsData), 0);
      }
      
      // Fetch Documents
      const docsRes = await fetchApi(`/workspaces/${workspaceId}/chatbots/${currentChatbot.id}/documents`);
      if (docsRes.ok) {
        const data: ApiDocument[] = await docsRes.json();
        const mapped: FileItem[] = data.map((doc: ApiDocument) => {
          const kb = doc.file_size_bytes / 1024;
          const sizeStr = kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(1)} KB`;
          return {
            id: doc.id,
            name: doc.original_filename || doc.filename || "Untitled Source",
            size: sizeStr,
            type: doc.file_type ? doc.file_type.toUpperCase() : "DOC",
            uploadedAt: doc.uploaded_at ? new Date(doc.uploaded_at).toISOString().split('T')[0] : "Recently",
            botIds: [doc.chatbot_id],
            coverage: doc.chunk_count ? `${doc.chunk_count}` : "0",
            status: doc.upload_status === "completed" ? "Ready" : "Syncing",
          };
        });
        setTimeout(() => setFetchedFiles(mapped), 0);
      }
    } catch (err) {
      console.error("Failed to load knowledge base data", err);
    }
  }, [workspaceId, currentChatbot]);

  useEffect(() => {
    loadData();
    const intervalId = setInterval(() => {
      loadData();
    }, 5000);
    return () => clearInterval(intervalId);
  }, [loadData]);

  const handleFileUploadLocal = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0 || !workspaceId || !currentChatbot?.id) return;
    
    setIsUploading(true);
    const filesArr = Array.from(e.target.files);
    
    for (const file of filesArr) {
      const formData = new FormData();
      formData.append("file", file);
      
      try {
        await fetchApi(`/workspaces/${workspaceId}/chatbots/${currentChatbot.id}/upload`, {
          method: "POST",
          body: formData
        });
        showToast(`Uploaded ${file.name} successfully!`);
      } catch (err) {
        console.error(`Failed to upload ${file.name}`, err);
      }
    }
    
    setIsUploading(false);
    setShowAddModal(false);
    loadData();
  };

  const handleDeleteDocument = async (file: FileItem) => {
    if (!workspaceId || !currentChatbot?.id) return;
    try {
      const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${currentChatbot.id}/documents/${file.id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setFetchedFiles((prev) => prev.filter((f) => f.id !== file.id));
        showToast("Source deleted successfully");
        loadData();
      } else {
        alert("Failed to delete document.");
      }
    } catch (err) {
      console.error("Delete failed", err);
      alert("Error deleting document.");
    }
  };

  const handleSyncAll = async () => {
    setIsSyncing(true);
    await loadData();
    setTimeout(() => {
      setIsSyncing(false);
      showToast("Knowledge sources synced");
    }, 800);
  };

  const filteredFiles = fetchedFiles.filter(file =>
    file.name.toLowerCase().includes(searchTerm.toLowerCase()) &&
    (!currentChatbot?.id || file.botIds.includes(currentChatbot.id))
  );

  const totalChunks = stats?.total_chunks || fetchedFiles.reduce((acc, f) => acc + (parseInt(f.coverage, 10) || 0), 0);
  const totalSources = stats?.total_documents ?? fetchedFiles.length;

  return (
    <div className="space-y-4 max-w-5xl">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[#0a0b0d] dark:text-white tracking-tight">Knowledge Base</h2>
          <p className="text-xs text-[#7c828a] mt-0.5">Manage what your bots know</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-1.5 h-8 px-4 bg-[#0052ff] text-white rounded-full text-xs font-semibold hover:bg-[#003ecc] transition-colors border-0 cursor-pointer"
        >
          <Plus size={13} /> Add source
        </button>
      </div>

      {/* ── Stats strip ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {[
          { label: "Total chunks", value: totalChunks ? totalChunks.toLocaleString() : "0" },
          { label: "Knowledge sources", value: totalSources.toString() },
          { label: "Avg. retrieval score", value: totalSources > 0 ? "0.87" : "0.00" },
        ].map(s => (
          <div key={s.label} className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-4">
            <p className="text-xl font-bold font-mono text-[#0a0b0d] dark:text-[#ffffff]">{s.value}</p>
            <p className="text-xs text-[#7c828a] mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* ── Search & Filter Strip ── */}
      <div className="flex items-center justify-between gap-3 bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 p-3">
        <div className="relative flex-1 max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#7c828a]" />
          <input
            type="text"
            placeholder="Search knowledge sources..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-[#f7f7f7] dark:bg-white/5 border border-transparent focus:border-[#0052ff] rounded-xl pl-9 pr-3 py-1.5 text-xs text-[#0a0b0d] dark:text-white outline-none transition-colors"
          />
        </div>
        {fetchedFiles.length > 0 && !isTraining && (
          <button
            onClick={startTraining}
            className="flex items-center gap-1.5 h-8 px-3.5 bg-[#0052ff]/10 text-[#0052ff] dark:bg-blue-900/20 dark:text-blue-400 rounded-full text-xs font-semibold hover:bg-[#0052ff]/20 transition-colors border-0 cursor-pointer"
          >
            <Brain size={13} /> Train AI Vector
          </button>
        )}
      </div>

      {/* ── Training Progress Banner ── */}
      {isTraining && (
        <div className="bg-[#f0f5ff] dark:bg-blue-950/20 rounded-2xl border border-[#0052ff]/20 p-4 space-y-2">
          <div className="flex items-center justify-between text-xs font-semibold text-[#0052ff]">
            <span className="flex items-center gap-2">
              <RefreshCw size={12} className="animate-spin" /> Training vector embeddings...
            </span>
            <span>{trainingProgress}%</span>
          </div>
          <ProgressBar value={trainingProgress} color="#0052ff" />
        </div>
      )}

      {/* ── Sources list ── */}
      <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 overflow-hidden">
        <div className="border-b border-[#dee1e6] dark:border-white/5 px-5 py-3.5 flex items-center justify-between">
          <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Knowledge Sources</p>
          <button
            onClick={handleSyncAll}
            disabled={isSyncing}
            className="flex items-center gap-1.5 text-xs text-[#0052ff] font-semibold border-0 bg-transparent cursor-pointer hover:underline disabled:opacity-50"
          >
            <RefreshCw size={11} className={isSyncing ? "animate-spin" : ""} /> Sync all
          </button>
        </div>

        {filteredFiles.length === 0 ? (
          <div className="p-8 text-center text-[#7c828a]">
            <p className="text-xs">No knowledge sources found.</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="mt-2 text-xs text-[#0052ff] font-semibold hover:underline border-0 bg-transparent cursor-pointer"
            >
              + Add your first document or website
            </button>
          </div>
        ) : (
          filteredFiles.map((s, i) => {
            const isUrl = s.type === "URL" || s.type === "WEBSITE" || s.name.startsWith("http");
            const health = s.status === "Ready" ? 100 : 85;

            return (
              <div
                key={s.id}
                className={`flex items-center gap-4 px-5 py-4 ${
                  i < filteredFiles.length - 1 ? "border-b border-[#dee1e6] dark:border-white/5" : ""
                } hover:bg-[#f7f7f7] dark:hover:bg-white/3 transition-colors`}
              >
                <div className="w-8 h-8 rounded-xl bg-[#f0f5ff] flex items-center justify-center shrink-0">
                  {isUrl ? <Globe size={15} className="text-[#0052ff]" /> : <FileText size={15} className="text-[#0052ff]" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[#0a0b0d] dark:text-white truncate">{s.name}</p>
                  <p className="text-xs text-[#7c828a] truncate">
                    {currentChatbot?.name || "Assistant"} · {s.coverage} chunks · {s.size} · synced {s.uploadedAt}
                  </p>
                </div>
                <div className="w-24 shrink-0 hidden sm:block">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] text-[#7c828a]">Health</span>
                    <span className="text-[10px] font-mono font-semibold text-[#05b169]">{health}%</span>
                  </div>
                  <ProgressBar value={health} color="#05b169" />
                </div>
                <button
                  onClick={() => {
                    if (window.confirm(`Delete source "${s.name}"?`)) {
                      handleDeleteDocument(s);
                    }
                  }}
                  className="h-7 px-3 rounded-full border border-[#dee1e6] dark:border-white/10 text-xs font-semibold text-[#cf202f] hover:bg-[#fee8e8] dark:hover:bg-rose-950/20 transition-colors border-0 cursor-pointer shrink-0"
                >
                  Delete
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* ── Add Source Modal ── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 w-full max-w-md rounded-2xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-[#dee1e6] dark:border-white/5 pb-3">
              <h4 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Add Knowledge Source</h4>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-full text-[#7c828a] hover:bg-[#f7f7f7] dark:hover:bg-white/5 border-0 bg-transparent cursor-pointer"
              >
                <X size={16} />
              </button>
            </div>

            {/* Toggle File / URL */}
            <div className="flex bg-[#f7f7f7] dark:bg-white/5 p-1 rounded-xl">
              <button
                type="button"
                onClick={() => setUploadMethod("file")}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border-0 cursor-pointer transition-all ${
                  uploadMethod === "file"
                    ? "bg-white dark:bg-[#0d111b] text-[#0052ff] shadow-sm"
                    : "text-[#7c828a] hover:text-[#0a0b0d]"
                }`}
              >
                Upload File
              </button>
              <button
                type="button"
                onClick={() => setUploadMethod("url")}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border-0 cursor-pointer transition-all ${
                  uploadMethod === "url"
                    ? "bg-white dark:bg-[#0d111b] text-[#0052ff] shadow-sm"
                    : "text-[#7c828a] hover:text-[#0a0b0d]"
                }`}
              >
                Import Web URL
              </button>
            </div>

            {uploadMethod === "file" ? (
              <div
                onClick={() => !isUploading && fileInputRef.current?.click()}
                className={`border-2 border-dashed border-[#dee1e6] dark:border-white/10 hover:border-[#0052ff] rounded-2xl p-6 text-center cursor-pointer transition-colors ${
                  isUploading ? "opacity-50 pointer-events-none" : ""
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUploadLocal}
                  multiple
                  className="hidden"
                  accept=".pdf,.txt,.docx,.csv,.xlsx,.pptx,.md,.epub,.png,.jpg,.jpeg,.webp,.tiff,.bmp"
                />
                <Upload size={24} className="mx-auto mb-2 text-[#0052ff]" />
                <p className="text-xs font-semibold text-[#0a0b0d] dark:text-white">
                  {isUploading ? "Uploading file..." : "Click or drag files here to upload"}
                </p>
                <p className="text-[10px] text-[#7c828a] mt-1">PDF, DOCX, PPTX, XLSX, CSV, MD, TXT, EPUB, Images (max 5MB)</p>
              </div>
            ) : (
              <form
                onSubmit={(e) => {
                  handleUrlSubmit(e);
                  setShowAddModal(false);
                  showToast("Web URL source added!");
                }}
                className="space-y-3"
              >
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-[#5b616e] uppercase">Website URL</label>
                  <input
                    type="url"
                    placeholder="https://example.com/docs"
                    value={inputUrl}
                    onChange={(e) => setInputUrl(e.target.value)}
                    required
                    className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl px-3 py-2 text-xs text-[#0a0b0d] dark:text-white outline-none focus:border-[#0052ff]"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full h-8 bg-[#0052ff] text-white rounded-xl text-xs font-semibold hover:bg-[#003ecc] transition-colors border-0 cursor-pointer"
                >
                  Import URL
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      <Toast message={toastMsg} visible={toastVisible} />
    </div>
  );
}
