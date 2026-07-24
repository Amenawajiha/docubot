"use client";

import React, { useState, useEffect } from "react";
import {
  User, Bell, Lock, Building, Upload, Shield, X, Eye, EyeOff, Loader2,
  Key, Webhook, Plus, Trash2, Copy, Check
} from "lucide-react";
import { useAuth, useWorkspace } from "@/components/providers/Providers";
import { fetchApi } from "@/lib/api";
import { Toast } from "@/components/ui/shared-dashboard";

export default function SettingsForm() {
  const [activeTab, setActiveTab] = useState<"profile" | "notifications" | "security" | "workspace" | "apikeys" | "webhooks">("profile");

  const { user, setUser } = useAuth();
  const { workspaceId } = useWorkspace();

  // Profile States
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);

  // Notification Preferences States
  const [alerts, setAlerts] = useState(true);
  const [summary, setSummary] = useState(true);
  const [updates, setUpdates] = useState(false);
  const [lowConfidence, setLowConfidence] = useState(true);

  // Workspace States
  const [workspaceName, setWorkspaceName] = useState("");
  const [timezone, setTimezone] = useState("(UTC-05:00) Eastern Time");
  const [isSavingWorkspace, setIsSavingWorkspace] = useState(false);

  // Password Modal States
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const [showPasswords, setShowPasswords] = useState({ current: false, new: false, confirm: false });

  // API Key States
  const [apiKeys, setApiKeys] = useState([
    { id: "1", name: "Production Bot Key", key: "sk_live_...9f2a", created: "2 weeks ago" },
    { id: "2", name: "Staging Test Key", key: "sk_test_...3a1c", created: "1 month ago" },
  ]);
  const [copiedKeyId, setCopiedKeyId] = useState<string | null>(null);
  const [toastMsg, setToastMsg] = useState("");
  const [toastVisible, setToastVisible] = useState(false);

  // Load User Data
  useEffect(() => {
    if (user) {
      const parts = (user.full_name || "").trim().split(" ");
      setFirstName(parts[0] || "");
      setLastName(parts.slice(1).join(" ") || "");
      setEmail(user.email || "");
    }
  }, [user]);

  // Load Workspace Data
  useEffect(() => {
    const fetchWorkspaceDetails = async () => {
      if (!workspaceId) return;
      try {
        const res = await fetchApi(`/workspaces/${workspaceId}`);
        if (res.ok) {
          const data = await res.json();
          setWorkspaceName(data.name || "");
          setTimezone(data.settings?.timezone || "(UTC-05:00) Eastern Time");
        }
      } catch (err) {
        console.error("Failed to fetch workspace details", err);
      }
    };
    fetchWorkspaceDetails();
  }, [workspaceId]);

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setToastVisible(true);
    setTimeout(() => setToastVisible(false), 2500);
  };

  const copyKey = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKeyId(id);
    showToast("API key copied to clipboard!");
    setTimeout(() => setCopiedKeyId(null), 2000);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingProfile(true);
    try {
      const payload = {
        full_name: `${firstName} ${lastName}`.trim(),
        email: email,
      };
      const res = await fetchApi("/auth/me", {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const updatedUser = await res.json();
        setUser(updatedUser);
        showToast("Profile settings updated successfully!");
      } else {
        const errData = await res.json();
        alert(errData.detail || "Failed to update profile settings.");
      }
    } catch (err) {
      console.error(err);
      alert("Error saving profile settings");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleSaveWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!workspaceId) return;
    setIsSavingWorkspace(true);
    try {
      const payload = {
        name: workspaceName,
        settings: { timezone: timezone },
      };
      const res = await fetchApi(`/workspaces/${workspaceId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        showToast("Workspace settings updated successfully!");
      } else {
        alert("Failed to update workspace settings.");
      }
    } catch (err) {
      console.error(err);
      alert("Error saving workspace settings");
    } finally {
      setIsSavingWorkspace(false);
    }
  };

  const handleChangePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordError("");
    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError("Password must be at least 8 characters long.");
      return;
    }
    setIsChangingPassword(true);
    try {
      const res = await fetchApi("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      if (res.ok) {
        const userRes = await fetchApi("/auth/me");
        if (userRes.ok) {
          const updatedUser = await userRes.json();
          setUser(updatedUser);
        }
        showToast("Password changed successfully!");
        setShowPasswordModal(false);
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
      } else {
        const errData = await res.json();
        setPasswordError(errData.detail || "Failed to change password.");
      }
    } catch (err) {
      console.error(err);
      setPasswordError("An error occurred. Please try again.");
    } finally {
      setIsChangingPassword(false);
    }
  };

  const getPasswordLastChangedText = () => {
    if (!user?.password_last_changed) return "Last changed: never";
    const lastChangedDate = new Date(user.password_last_changed);
    const now = new Date();
    const diffTime = Math.abs(now.getTime() - lastChangedDate.getTime());
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    const diffMonths = Math.floor(diffDays / 30);
    
    if (diffMonths >= 1) {
      return `Last changed ${diffMonths} month${diffMonths > 1 ? "s" : ""} ago`;
    } else if (diffDays >= 1) {
      return `Last changed ${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
    } else {
      return "Last changed today";
    }
  };

  const tabs = [
    { id: "profile", label: "Profile", icon: User },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "security", label: "Security", icon: Lock },
    { id: "workspace", label: "Workspace", icon: Building },
    { id: "apikeys", label: "API Keys", icon: Key },
    { id: "webhooks", label: "Webhooks", icon: Webhook },
  ] as const;

  const initials = `${firstName?.charAt(0) || ""}${lastName?.charAt(0) || ""}`.toUpperCase();

  return (
    <div className="space-y-6 max-w-5xl">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-[#0a0b0d] dark:text-white tracking-tight">Settings</h2>
        <p className="text-xs text-[#7c828a] mt-0.5">Manage your account, API keys, notifications, and workspace preferences.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-start">
        {/* Left Tabs Bar */}
        <div className="md:col-span-1 p-2 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-xl text-xs font-semibold border-0 cursor-pointer text-left transition-all ${
                  isActive
                    ? "bg-[#f0f5ff] text-[#0052ff] dark:bg-blue-900/10 dark:text-blue-450"
                    : "text-[#5b616e] hover:text-[#0a0b0d] dark:text-slate-400 dark:hover:text-white hover:bg-[#f7f7f7] dark:hover:bg-white/5 bg-transparent"
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isActive ? "text-[#0052ff]" : "text-[#7c828a]"}`} />
                <span className="truncate">{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Right Content */}
        <div className="md:col-span-3 space-y-6">
          {/* PROFILE */}
          {activeTab === "profile" && (
            <div className="space-y-4 animate-fadeIn">
              <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-4">
                <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Profile Photo</h3>
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-full bg-[#0052ff] text-white flex items-center justify-center font-bold text-sm shrink-0">
                    {initials || "U"}
                  </div>
                  <div className="space-y-1">
                    <button
                      type="button"
                      onClick={() => alert("Upload dialog trigger...")}
                      className="px-3 py-1.5 border border-[#dee1e6] rounded-xl text-xs font-semibold bg-white text-[#5b616e] hover:bg-[#f7f7f7] transition-colors"
                    >
                      Upload photo
                    </button>
                    <p className="text-[10px] text-[#7c828a]">JPG or PNG. Max size 2MB.</p>
                  </div>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-4">
                <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Personal Details</h3>
                <form onSubmit={handleSaveProfile} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">First Name</label>
                      <input
                        type="text"
                        value={firstName}
                        required
                        onChange={(e) => setFirstName(e.target.value)}
                        className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl px-3 py-2 text-sm text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">Last Name</label>
                      <input
                        type="text"
                        value={lastName}
                        required
                        onChange={(e) => setLastName(e.target.value)}
                        className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl px-3 py-2 text-sm text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">Email Address</label>
                    <input
                      type="email"
                      value={email}
                      required
                      onChange={(e) => setEmail(e.target.value)}
                      className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl px-3 py-2 text-sm text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                    />
                  </div>
                    <button
                      type="submit"
                      disabled={isSavingProfile}
                    className="bg-[#0052ff] hover:bg-[#003ecc] text-white px-4 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                    >
                    {isSavingProfile ? <Loader2 size={12} className="animate-spin" /> : null}
                        <span>Save Changes</span>
                    </button>
                </form>
              </div>
            </div>
          )}

          {/* NOTIFICATIONS */}
          {activeTab === "notifications" && (
            <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-4 animate-fadeIn">
              <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Notification Preferences</h3>
              <div className="divide-y divide-[#dee1e6] dark:divide-white/5">
                {[
                  { title: "New conversation alerts", desc: "Get notified when a customer starts a chat", value: alerts, setter: setAlerts },
                  { title: "Weekly performance summary", desc: "A digest of bot activity every Monday morning", value: summary, setter: setSummary },
                  { title: "Product updates", desc: "News about new DocuBot features", value: updates, setter: setUpdates },
                  { title: "Low confidence answer alerts", desc: "Notify me when the AI flags a response as needing review", value: lowConfidence, setter: setLowConfidence }
                ].map((item, idx) => (
                  <div key={item.title} className={`flex items-center justify-between py-3.5 ${idx === 0 ? "pt-0" : ""}`}>
                    <div>
                      <p className="text-xs font-semibold text-[#0a0b0d] dark:text-white">{item.title}</p>
                      <p className="text-[10px] text-[#7c828a] mt-0.5">{item.desc}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => item.setter(!item.value)}
                      className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-205 ${
                        item.value ? "bg-[#0052ff]" : "bg-[#eef0f3] dark:bg-white/10"
                      }`}
                    >
                      <span className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white transition duration-205 ${item.value ? "translate-x-4" : "translate-x-0"}`} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* SECURITY */}
          {activeTab === "security" && (
            <div className="space-y-4 animate-fadeIn">
              <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-4">
                <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Password</h3>
                <div className="space-y-3 font-medium">
                  <p className="text-xs text-slate-500">{getPasswordLastChangedText()}</p>
                  <button
                    type="button"
                    onClick={() => setShowPasswordModal(true)}
                    className="px-3 py-1.5 border border-[#dee1e6] rounded-xl text-xs font-semibold bg-white text-[#5b616e] hover:bg-[#f7f7f7] transition-colors"
                  >
                    Change password
                  </button>
                </div>
              </div>

              <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white flex items-center gap-2">
                    <Shield className="w-4 h-4 text-[#0052ff]" /> Two-factor authentication
                  </h3>
                  <p className="text-[10px] text-[#7c828a] mt-0.5">Add an extra layer of security to your account</p>
                </div>
                <button
                  type="button"
                  onClick={() => alert("Setting up Multi-Factor authentication...")}
                  className="px-3 py-1.5 border border-[#dee1e6] rounded-xl text-xs font-semibold bg-white text-[#5b616e] hover:bg-[#f7f7f7] transition-colors shrink-0"
                >
                  Enable
                </button>
              </div>
            </div>
          )}

          {/* WORKSPACE */}
          {activeTab === "workspace" && (
            <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-4 animate-fadeIn">
              <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Workspace Details</h3>
              <form onSubmit={handleSaveWorkspace} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">Workspace Name</label>
                  <input
                    type="text"
                    value={workspaceName}
                    required
                    onChange={(e) => setWorkspaceName(e.target.value)}
                    className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl px-3 py-2 text-sm text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">Time Zone</label>
                  <select
                    value={timezone}
                    onChange={(e) => setTimezone(e.target.value)}
                    className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl px-3 py-2 text-sm text-[#0a0b0d] dark:text-white focus:border-[#0052ff] outline-none"
                  >
                    <option value="(UTC-05:00) Eastern Time">(UTC-05:00) Eastern Time</option>
                    <option value="(UTC+00:00) UTC">(UTC+00:00) UTC</option>
                    <option value="(UTC+05:30) India Standard Time">(UTC+05:30) India Standard Time</option>
                  </select>
                </div>

                  <button
                    type="submit"
                    disabled={isSavingWorkspace}
                  className="bg-[#0052ff] hover:bg-[#003ecc] text-white px-4 py-2 rounded-xl text-xs font-semibold transition-colors flex items-center space-x-1.5 disabled:opacity-50"
                  >
                  {isSavingWorkspace ? <Loader2 size={12} className="animate-spin" /> : null}
                      <span>Save Changes</span>
                  </button>
              </form>
            </div>
          )}

          {/* API KEYS */}
          {activeTab === "apikeys" && (
            <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">API Keys</h3>
                <button
                  type="button"
                  onClick={() => {
                    const newKey = {
                      id: Date.now().toString(),
                      name: `New Key ${apiKeys.length + 1}`,
                      key: `sk_live_...${Math.random().toString(36).substring(2, 6)}`,
                      created: "Just now"
                    };
                    setApiKeys(k => [...k, newKey]);
                    showToast("New API Key generated successfully!");
                  }}
                  className="flex items-center gap-1.5 h-8 px-3 bg-[#0052ff] text-white rounded-full text-xs font-semibold hover:bg-[#003ecc] transition-colors"
                >
                  <Plus size={12} /> Generate Key
                </button>
              </div>
              <p className="text-xs text-[#7c828a]">Generate API keys to integrate DocuBot features programmatically into your backends or pipelines.</p>
              
              <div className="divide-y divide-[#dee1e6] dark:divide-white/5">
                {apiKeys.map((k) => (
                  <div key={k.id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-xs font-semibold text-[#0a0b0d] dark:text-white">{k.name}</p>
                      <p className="text-[10px] text-[#7c828a] mt-0.5">Created {k.created}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <code className="text-xs font-mono bg-[#f7f7f7] dark:bg-white/5 px-2 py-1 rounded text-[#5b616e] dark:text-slate-350">{k.key}</code>
                      <button
                        onClick={() => copyKey(k.id, k.key)}
                        className="w-7 h-7 rounded-lg border border-[#dee1e6] flex items-center justify-center hover:bg-[#f7f7f7] dark:hover:bg-white/5 transition-colors"
                      >
                        {copiedKeyId === k.id ? <Check size={12} className="text-[#05b169]" /> : <Copy size={12} className="text-[#7c828a]" />}
                      </button>
                      <button
                        onClick={() => {
                          setApiKeys(keys => keys.filter(key => key.id !== k.id));
                          showToast("API Key revoked successfully.");
                        }}
                        className="w-7 h-7 rounded-lg border border-[#dee1e6] flex items-center justify-center hover:bg-[#fee8e8] text-[#cf202f] transition-colors"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* WEBHOOKS */}
          {activeTab === "webhooks" && (
            <div className="p-5 rounded-2xl bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 space-y-4 animate-fadeIn">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Webhooks</h3>
                <button
                  type="button"
                  onClick={() => alert("Creating webhook...")}
                  className="flex items-center gap-1.5 h-8 px-3 bg-[#0052ff] text-white rounded-full text-xs font-semibold hover:bg-[#003ecc] transition-colors"
                >
                  <Plus size={12} /> Add Webhook
                </button>
              </div>
              <p className="text-xs text-[#7c828a]">Send real-time alerts or event notifications to external webhooks when chats occur or bots require human assistance.</p>
              
              <div className="border border-dashed border-[#dee1e6] dark:border-white/5 rounded-2xl p-6 text-center bg-[#f7f7f7]/30 dark:bg-transparent">
                <Webhook size={28} className="mx-auto mb-2 text-[#a8acb3]" />
                <p className="font-semibold text-sm text-[#0a0b0d] dark:text-white">No webhooks registered</p>
                <p className="text-xs text-[#7c828a] mt-0.5">Click the button above to register your first webhook URL.</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Change Password Dialog Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 backdrop-blur-sm p-4 animate-fadeIn">
          <div className="bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/5 w-full max-w-md rounded-2xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-semibold text-[#0a0b0d] dark:text-white">Change Password</h4>
              <button
                type="button"
                onClick={() => setShowPasswordModal(false)}
                className="p-1 rounded-full text-slate-400 hover:bg-slate-100 dark:hover:bg-white/5 border-0 bg-transparent cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleChangePasswordSubmit} className="space-y-4">
              {passwordError && (
                <div className="p-3 text-xs text-rose-500 bg-rose-50 border border-rose-200 rounded-xl font-medium">
                  {passwordError}
                </div>
              )}
              
              <div className="space-y-1.5 relative">
                <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">Current Password</label>
                <input
                  type={showPasswords.current ? "text" : "password"}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  placeholder="Enter current password"
                  className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl pl-3 pr-10 py-2 text-sm text-[#0a0b0d] dark:text-white focus:outline-none focus:border-[#0052ff]"
                />
                <button
                  type="button"
                  onClick={() => setShowPasswords(prev => ({ ...prev, current: !prev.current }))}
                  className="absolute right-3.5 top-[27px] text-slate-400 hover:text-slate-650 border-0 bg-transparent cursor-pointer"
                >
                  {showPasswords.current ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>

              <div className="space-y-1.5 relative">
                <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">New Password</label>
                <input
                  type={showPasswords.new ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  placeholder="Enter new password"
                  className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl pl-3 pr-10 py-2 text-sm text-[#0a0b0d] dark:text-white focus:outline-none focus:border-[#0052ff]"
                />
                <button
                  type="button"
                  onClick={() => setShowPasswords(prev => ({ ...prev, new: !prev.new }))}
                  className="absolute right-3.5 top-[27px] text-slate-400 hover:text-slate-650 border-0 bg-transparent cursor-pointer"
                >
                  {showPasswords.new ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>

              <div className="space-y-1.5 relative">
                <label className="text-[10px] font-bold text-[#5b616e] uppercase tracking-wide">Confirm New Password</label>
                <input
                  type={showPasswords.confirm ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  placeholder="Confirm new password"
                  className="w-full bg-white dark:bg-[#0d111b] border border-[#dee1e6] dark:border-white/10 rounded-xl pl-3 pr-10 py-2 text-sm text-[#0a0b0d] dark:text-white focus:outline-none focus:border-[#0052ff]"
                />
                <button
                  type="button"
                  onClick={() => setShowPasswords(prev => ({ ...prev, confirm: !prev.confirm }))}
                  className="absolute right-3.5 top-[27px] text-slate-400 hover:text-slate-650 border-0 bg-transparent cursor-pointer"
                >
                  {showPasswords.confirm ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowPasswordModal(false)}
                  className="px-3.5 py-2 border border-[#dee1e6] rounded-xl text-xs font-semibold bg-[#ffffff] text-[#5b616e] hover:bg-[#f7f7f7] cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isChangingPassword}
                  className="bg-[#0052ff] hover:bg-[#003ecc] text-white px-4 py-2 rounded-xl text-xs font-semibold flex items-center space-x-1.5 disabled:opacity-50"
                >
                  {isChangingPassword ? <Loader2 size={12} className="animate-spin" /> : null}
                    <span>Change Password</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <Toast message={toastMsg} visible={toastVisible} />
    </div>
  );
}
