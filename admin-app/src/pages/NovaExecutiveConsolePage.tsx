import React, { useState, useEffect, useRef } from 'react';
import {
  Sparkles,
  Mic,
  MicOff,
  Send,
  Square,
  Volume2,
  VolumeX,
  CheckCircle2,
  ShieldAlert,
  Bell,
  FolderKanban,
  ArrowUpRight,
  Clock
} from 'lucide-react';
import { useNexus } from '../context/NexusContext';
import { TruthBadge } from '../components/common/TruthBadge';
import { NovaAvatarStage } from '../components/nova/NovaAvatarStage';
import { ASSETS } from '../data/assets';
import { NovaVideo } from '../components/nova/NovaVideo';
import { UnavailableState } from '../components/live/UnavailableState';

export const NovaExecutiveConsolePage: React.FC = () => {
  const {
    messages,
    quickActions,
    novaState,
    setNovaState,
    isMuted,
    setIsMuted,
    projects,
    approvals,
    notifications,
    unreadNotificationsCount,
    approveDecision,
    navigateToObject,
    markNotificationRead,
    markAllNotificationsRead,
    liveAreas,
  } = useNexus();

  const [inputText, setInputText] = useState('');
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const pendingApprovals = approvals.filter(a => a.status === 'PENDING');
  const activeProjects = projects.filter(p => p.status === 'ACTIVE' || p.status === 'AWAITING_APPROVAL');

  const handleToggleListening = () => setIsListening(false);

  const handleStop = () => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.cancel();
    }
    setNovaState('idle');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setInputText('');
  };

  return (
    <div className="space-y-4 pb-10">
      {/* Header + Primary Question */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600" />
            <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
              Nova Operator Console
            </h1>
            <TruthBadge truth="VERIFIED" label="Single Authoritative State" />
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            What does Nexus need to tell me, and what can I ask it to do? Powered by the exact same project &amp; approval state as Admin.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 font-medium">
            {activeProjects.length} Active Projects
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-amber-50 text-amber-800 border border-amber-200 font-medium">
            {pendingApprovals.length} Pending Approvals
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 font-medium">
            Nova: {liveAreas.nova?.service || 'UNKNOWN'}
          </span>
        </div>
      </div>

      {/* Main Split Workspace: Left Operator Chat + Controls | Right Live Notifications, Projects & Approvals */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT (7 cols): Grounded Operator Conversation + Voice Controls */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200/80 shadow-2xs flex flex-col h-[640px] overflow-hidden">
          <div className="p-3.5 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50/50 shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full overflow-hidden border border-blue-200 bg-slate-900 shrink-0 shadow-2xs">
                <NovaVideo
                  aria-label="Nova"
                  className="w-full h-full object-cover object-[50%_18%]"
                />
              </div>
              <div>
                <div className="text-sm font-semibold text-slate-900">Nova Control-Plane Query</div>
                <div className="text-[11px] text-slate-500">
                  Read-only project and approval state from the live Nexus read model
                </div>
              </div>
            </div>

            {/* Compact Voice Toolbar */}
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                disabled
                onClick={handleToggleListening}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-medium inline-flex items-center gap-1 cursor-pointer ${
                  isListening
                    ? 'bg-rose-600 text-white animate-pulse'
                    : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`}
              >
                {isListening ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
                {isListening ? 'Listening...' : 'Voice'}
              </button>
              <button
                type="button"
                onClick={handleStop}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 cursor-pointer"
                title="Stop Speech"
              >
                <Square className="w-3.5 h-3.5 text-rose-500" />
              </button>
              <button
                type="button"
                onClick={() => setIsMuted(!isMuted)}
                className="p-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-slate-600 cursor-pointer"
                title={isMuted ? 'Unmute Voice' : 'Mute Voice'}
              >
                {isMuted ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Quick Grounded Prompts */}
          <div className="px-3.5 py-2 border-b border-slate-100 flex flex-wrap gap-1.5 bg-white shrink-0">
            {quickActions.map(q => (
              <button
                key={q}
                type="button"
                disabled
                className="px-2.5 py-1 rounded-lg bg-slate-50 border border-slate-200 text-[11px] font-medium text-slate-400 cursor-not-allowed"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Chat Thread */}
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-4 space-y-3">
            <UnavailableState>Nova conversation transport is not connected in Admin. Service status and current durable activity are shown from live Nexus records.</UnavailableState>
            {false && messages.map(msg => {
              const isNova = msg.sender === 'nova';
              return (
                <div
                  key={msg.id}
                  className={`flex items-start gap-2.5 ${isNova ? 'justify-start' : 'justify-end'}`}
                >
                  {isNova && (
                    <div className="w-7 h-7 rounded-lg bg-blue-50 border border-blue-200 text-blue-600 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="w-3.5 h-3.5" />
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] rounded-xl px-3.5 py-2.5 text-xs leading-relaxed ${
                      isNova
                        ? 'bg-slate-50 border border-slate-200/80 text-slate-800'
                        : 'bg-blue-600 text-white'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3 mb-1 text-[10px]">
                      <span className={isNova ? 'font-semibold text-blue-700' : 'text-blue-100'}>
                        {isNova ? 'Nova' : 'Ray Davis'}
                      </span>
                      <span className={isNova ? 'text-slate-400' : 'text-blue-100'}>
                        {msg.timestamp}
                      </span>
                    </div>
                    <p className="whitespace-pre-line">{msg.text}</p>
                  </div>
                </div>
              );
            })}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <form
            onSubmit={handleSubmit}
            className="p-3 border-t border-slate-100 bg-slate-50/50 flex items-center gap-2 shrink-0"
          >
              <input
              type="text"
              value={inputText}
                onChange={() => setInputText('')}
                placeholder="Nova conversation transport not connected"
                disabled
              className="flex-1 px-3 py-2 text-xs bg-white border border-slate-200 rounded-lg focus:outline-hidden focus:border-blue-500"
            />
            <button
              type="submit"
              disabled
              className="px-4 py-2 rounded-lg bg-blue-600 disabled:opacity-50 text-white text-xs font-medium inline-flex items-center gap-1.5 cursor-not-allowed"
            >
              Send <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </div>

        {/* RIGHT (5 cols): Nova Live Video Stage + Notifications, Active Projects & Needs Ray */}
        <div className="lg:col-span-5 space-y-4">
          {/* Nova Video Presence Stage */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs flex flex-col items-center">
            <div className="w-full flex items-center justify-between pb-2 border-b border-slate-100 mb-2">
              <span className="text-xs font-semibold text-slate-900">Nova Operator Presence</span>
              <span className="text-[11px] font-medium text-blue-600">Live Avatar</span>
            </div>
            <NovaAvatarStage state="idle" compact />
          </div>

          {/* Live Notifications Feed */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-2.5">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Bell className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-semibold text-slate-900">
                  Notifications &amp; Escalations ({unreadNotificationsCount} unread)
                </h2>
              </div>
              {unreadNotificationsCount > 0 && (
                <button
                  type="button"
                  onClick={markAllNotificationsRead}
                  className="text-[11px] font-medium text-blue-600 hover:underline cursor-pointer"
                >
                  Mark all read
                </button>
              )}
            </div>

            <div className="space-y-2 max-h-[220px] overflow-y-auto custom-scrollbar pr-1">
              {notifications.slice(0, 6).map(n => (
                <button
                  key={n.id}
                  type="button"
                  onClick={() => {
                    markNotificationRead(n.id);
                    navigateToObject(n.targetPage, n.targetEntityId);
                  }}
                  className={`w-full text-left p-2.5 rounded-lg border transition-colors cursor-pointer ${
                    n.read
                      ? 'bg-white border-slate-200/70 hover:bg-slate-50'
                      : 'bg-blue-50/50 border-blue-200 hover:bg-blue-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 text-[10px]">
                    <span className="font-semibold text-blue-700">{n.type.replace(/_/g, ' ')}</span>
                    <span className="text-slate-400 flex items-center gap-1">
                      <Clock className="w-2.5 h-2.5" />
                      {n.timestamp}
                    </span>
                  </div>
                  <div className="text-xs font-medium text-slate-900 mt-0.5">{n.title}</div>
                  <div className="text-[11px] text-slate-600 line-clamp-2 mt-0.5">{n.detail}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Pending Approvals Synced to ApprovalsPage */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-2.5">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                <h2 className="text-sm font-semibold text-slate-900">
                  Needs Ray ({pendingApprovals.length})
                </h2>
              </div>
              <button
                type="button"
                onClick={() => navigateToObject('approvals')}
                className="text-xs font-medium text-blue-600 hover:underline cursor-pointer"
              >
                Open Approvals →
              </button>
            </div>

            {pendingApprovals.length === 0 ? (
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                All pending Ray approvals resolved.
              </div>
            ) : (
              <div className="space-y-2 max-h-[190px] overflow-y-auto custom-scrollbar pr-1">
                {pendingApprovals.slice(0, 4).map(apr => (
                  <div
                    key={apr.id}
                    className="p-2.5 rounded-lg bg-amber-50/40 border border-amber-200/80 flex items-center justify-between gap-2 text-xs"
                  >
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-900 truncate">{apr.title}</div>
                      <div className="text-[11px] text-slate-500 truncate">
                        {apr.projectName} · {apr.type}
                      </div>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={() => approveDecision(apr.id, 'Approved via Nova Console')}
                        className="px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-medium cursor-pointer"
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        onClick={() => navigateToObject('approvals', apr.id, 'approval')}
                        className="px-2 py-1 rounded bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 text-[11px] font-medium cursor-pointer"
                      >
                        Review
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Authoritative Active Projects Strip */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-2xs space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FolderKanban className="w-4 h-4 text-blue-600" />
                <h2 className="text-sm font-semibold text-slate-900">Active Projects</h2>
              </div>
              <button
                type="button"
                onClick={() => navigateToObject('projects')}
                className="text-xs font-medium text-blue-600 hover:underline cursor-pointer"
              >
                All ({projects.length})
              </button>
            </div>
            <div className="space-y-1.5">
              {activeProjects.slice(0, 3).map(proj => (
                <button
                  key={proj.id}
                  type="button"
                  onClick={() => navigateToObject('projects', proj.id, 'project')}
                  className="w-full text-left p-2 rounded-lg bg-slate-50 hover:bg-slate-100 border border-slate-200/80 flex items-center justify-between gap-2 text-xs cursor-pointer"
                >
                  <div className="min-w-0">
                    <div className="font-medium text-slate-900 truncate">{proj.name}</div>
                    <div className="text-[11px] text-slate-500 truncate">
                      {proj.currentDepartment} · {proj.nextAction}
                    </div>
                  </div>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
