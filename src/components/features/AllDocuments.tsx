"use client";

import React, { useState, useEffect } from "react";
import { Search, Bot, FileText, ChevronDown, Trash2, Download, Filter } from "lucide-react";
import { useWorkspace, FileItem } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { DocStatusBadge } from "@/components/ui/shared-dashboard";

interface MappedFileItem extends FileItem {
  chunks: number;
}

export default function AllDocuments() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedBotFilter, setSelectedBotFilter] = useState("all");
  const [fetchedFiles, setFetchedFiles] = useState<MappedFileItem[]>([]);
  const [loading, setLoading] = useState(true);

  const { workspaceId, chatbots } = useWorkspace();

  useEffect(() => {
    if (!workspaceId) return;

    const fetchDocuments = async () => {
      setLoading(true);
      try {
        const res = await fetchApi(`/workspaces/${workspaceId}/documents`);
        if (res.ok) {
          const data = await res.json();
          // Map backend documents to frontend FileItem structure
          const mapped: MappedFileItem[] = data.map((doc: any) => {
            const kb = (doc.file_size_bytes || 0) / 1024;
            const sizeStr = kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb.toFixed(1)} KB`;
            const fileExt = (doc.file_type || doc.original_filename?.split('.').pop() || "file").toLowerCase();
            return {
              id: doc.id,
              name: doc.original_filename || doc.filename,
              size: sizeStr,
              type: fileExt,
              uploadedAt: doc.uploaded_at ? new Date(doc.uploaded_at).toISOString().split('T')[0] : "—",
              botIds: [doc.chatbot_id],
              coverage: doc.chunk_count ? "100%" : "0%",
              status: doc.upload_status === "completed" ? "Ready" : "Syncing",
              chunks: doc.chunk_count || 0,
            };
          });
          setFetchedFiles(mapped);
        }
      } catch (err) {
        console.error("Failed to fetch documents", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDocuments();
  }, [workspaceId]);

  // Filter documents by search term and chatbot association
  const filteredFiles = fetchedFiles.filter((file) => {
    const matchesSearch = file.name.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesBot = selectedBotFilter === "all" || file.botIds.includes(selectedBotFilter);
    return matchesSearch && matchesBot;
  });

  const handleDeleteDocument = async (file: FileItem) => {
    if (!workspaceId) return;
    const chatbotId = file.botIds[0];
    if (!chatbotId) return;

    try {
      const res = await fetchApi(`/workspaces/${workspaceId}/chatbots/${chatbotId}/documents/${file.id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        setFetchedFiles((prev) => prev.filter((f) => f.id !== file.id));
      } else {
        alert("Failed to delete document.");
      }
    } catch (err) {
      console.error("Delete failed", err);
      alert("Error deleting document.");
    }
  };

  // Helper to map botIds to chatbot names
  const getChatbotNames = (botIds: string[]) => {
    if (!botIds || botIds.length === 0) return "Global";
    return botIds
      .map((id) => chatbots.find((b) => b.id === id)?.name || "Unknown Bot")
      .join(", ");
  };

  const typeColor: Record<string, string> = {
    pdf: "#cf202f",
    docx: "#0052ff",
    doc: "#0052ff",
    csv: "#05b169",
    txt: "#7c828a",
    json: "#b07d00",
    file: "#a8acb3"
  };

  const totalChunks = fetchedFiles.reduce((acc, doc) => acc + (doc.chunks || 0), 0);

  return (
    <div className="space-y-6 max-w-5xl text-left animate-fadeIn">
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-[#0a0b0d] dark:text-white tracking-tight">Documents Library</h2>
          <p className="text-xs text-[#7c828a] mt-0.5">
            {fetchedFiles.length} {fetchedFiles.length === 1 ? "document" : "documents"} · {totalChunks.toLocaleString()} chunks indexed
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Table Search */}
          <div className="relative w-full sm:w-[220px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#a8acb3]" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-full pl-9 pr-3.5 py-1.5 text-xs text-[#0a0b0d] dark:text-white placeholder:text-[#a8acb3] focus:outline-none focus:border-[#0052ff] transition-all"
            />
          </div>

          {/* Chatbot Filter Dropdown */}
          <div className="relative shrink-0">
            <div className="flex items-center gap-1.5 h-8 px-3.5 rounded-full border border-[#dee1e6] bg-white dark:bg-[#0d111b] text-xs font-semibold text-[#5b616e] dark:text-slate-300 hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors cursor-pointer select-none">
              <Filter size={12} className="text-[#7c828a]" />
              <span className="max-w-[120px] truncate">
                {selectedBotFilter === "all"
                  ? "All Chatbots"
                  : chatbots.find((b) => b.id === selectedBotFilter)?.name || "Selected Bot"}
              </span>
              <ChevronDown className="w-3.5 h-3.5 text-[#7c828a] shrink-0 ml-0.5" />
            </div>
            <select
              value={selectedBotFilter}
              onChange={(e) => setSelectedBotFilter(e.target.value)}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            >
              <option value="all">All Chatbots</option>
              {chatbots.map((bot) => (
                <option key={bot.id} value={bot.id}>
                  {bot.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* ── Documents table ── */}
      <div className="bg-white dark:bg-[#0d111b] rounded-2xl border border-[#dee1e6] dark:border-white/5 overflow-hidden shadow-sm">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#dee1e6] dark:border-white/5 bg-[#f7f7f7] dark:bg-white/3">
                <th className="text-left px-5 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Document</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Size</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Chunks</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Chatbot</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Uploaded</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-[#7c828a] uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-[#7c828a] text-xs font-medium">
                    Loading documents...
                  </td>
                </tr>
              ) : filteredFiles.length > 0 ? (
                filteredFiles.map((doc, i) => (
                  <tr key={doc.id} className={`${i < filteredFiles.length - 1 ? "border-b border-[#dee1e6] dark:border-white/5" : ""} hover:bg-[#f7f7f7] dark:hover:bg-white/3 transition-colors group`}>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-[10px] font-bold text-white uppercase shrink-0" style={{ backgroundColor: typeColor[doc.type] || "#a8acb3" }}>
                          {doc.type}
                        </div>
                        <span className="font-medium text-[#0a0b0d] dark:text-white text-sm truncate max-w-[220px]">{doc.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5 text-xs text-[#7c828a] font-mono">{doc.size}</td>
                    <td className="px-4 py-3.5 text-xs font-mono text-[#0a0b0d] dark:text-white">{doc.chunks > 0 ? doc.chunks.toLocaleString() : "—"}</td>
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1.5 text-xs text-[#5b616e] dark:text-slate-300 font-medium">
                        <Bot className="w-3.5 h-3.5 text-[#7c828a] shrink-0" />
                        <span className="truncate max-w-[130px]">{getChatbotNames(doc.botIds)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5"><DocStatusBadge status={doc.status} /></td>
                    <td className="px-4 py-3.5 text-xs text-[#a8acb3]">{doc.uploadedAt}</td>
                    <td className="px-4 py-3.5 text-right">
                      <div className="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          type="button"
                          onClick={() => {
                            if (confirm(`Are you sure you want to permanently delete "${doc.name}"?`)) {
                              handleDeleteDocument(doc);
                            }
                          }}
                          className="w-7 h-7 rounded-lg hover:bg-[#fee8e8] flex items-center justify-center border-0 bg-transparent cursor-pointer transition-colors"
                          title="Delete Document"
                        >
                          <Trash2 size={13} className="text-[#cf202f]" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-[#7c828a] text-xs font-medium">
                    📂 No documents found matching the search or filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
