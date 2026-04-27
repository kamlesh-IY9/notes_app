/** Progress — live job progress view with SSE events. */

import { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type Job } from '../lib/api';
import { useSSE, type SSEEvent } from '../lib/sse';
import {
  Play, Pause, Square, Download, Clock, CheckCircle,
  XCircle, RotateCcw, ArrowLeft, Zap
} from 'lucide-react';

interface LiveEntry {
  entry_num: number;
  global_id: number;
  status: string;
  app_type?: string;
  theme?: string;
  title?: string;
  word_count?: number;
  entry_id?: string;
  persona_summary?: string;
}

export default function Progress() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<Job | null>(null);
  const [entries, setEntries] = useState<LiveEntry[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);

  // Load initial state
  useEffect(() => {
    if (!jobId) return;
    loadJob();
    loadEntries();
  }, [jobId]);

  async function loadJob() {
    if (!jobId) return;
    const j = await api.getJob(jobId);
    setJob(j);
    if (j.status === 'pending') {
      setStreaming(true);
    }
  }

  async function loadEntries() {
    if (!jobId) return;
    const res = await api.listEntries(jobId, { limit: '500' });
    setEntries(res.entries.map((e) => ({
      entry_num: e.entry_num,
      global_id: e.global_id,
      status: e.status,
      app_type: e.app_type,
      theme: e.theme,
      title: e.title || undefined,
      word_count: e.word_count,
      entry_id: e.id,
      persona_summary: '',
    })));
  }

  const handleSSE = useCallback((evt: SSEEvent) => {
    const d = evt.data as any;

    switch (evt.event) {
      case 'job_started':
        setJob((j) => j ? { ...j, status: 'running' } : j);
        addLog(`🚀 Job started — generating ${d.batch_size} entries`);
        break;
      case 'entry_started':
        addLog(`⏳ #${d.entry_num} (ID ${d.global_id}) started...`);
        break;
      case 'entry_completed':
        setEntries((prev) => [
          ...prev,
          {
            entry_num: d.entry_num,
            global_id: d.global_id,
            status: d.status,
            app_type: d.app_type,
            theme: d.theme,
            title: d.title,
            word_count: d.word_count,
            entry_id: d.entry_id,
            persona_summary: d.persona_summary,
          },
        ]);
        setJob((j) =>
          j ? {
            ...j,
            generated: (j.generated || 0) + 1,
            accepted: d.status === 'accepted' ? (j.accepted || 0) + 1 : j.accepted,
          } : j
        );
        const icon = d.status === 'accepted' ? '✅' : '❌';
        addLog(`${icon} #${d.entry_num} ${d.status} — ${d.app_type}/${d.theme} "${d.title || 'no-title'}" (${d.word_count}w)`);
        break;
      case 'entry_failed':
        addLog(`💥 #${d.entry_num} FAILED: ${d.error}`);
        setJob((j) => j ? { ...j, failed: (j.failed || 0) + 1 } : j);
        break;
      case 'job_completed':
        setJob((j) => j ? { ...j, status: 'completed' } : j);
        addLog('🎉 Job completed!');
        setStreaming(false);
        break;
      case 'job_cancelled':
        setJob((j) => j ? { ...j, status: 'cancelled' } : j);
        addLog('🛑 Job cancelled');
        setStreaming(false);
        break;
      case 'error':
        addLog(`❗ Error: ${d.message}`);
        break;
    }
  }, []);

  const { connected } = useSSE(streaming ? jobId || null : null, handleSSE);

  function addLog(msg: string) {
    setLog((prev) => [...prev.slice(-200), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  }

  async function handlePause() {
    if (!jobId) return;
    await api.pauseJob(jobId);
    setJob((j) => j ? { ...j, status: 'paused' } : j);
  }

  async function handleResume() {
    if (!jobId) return;
    await api.resumeJob(jobId);
    setJob((j) => j ? { ...j, status: 'running' } : j);
  }

  async function handleCancel() {
    if (!jobId || !confirm('Cancel this job?')) return;
    await api.cancelJob(jobId);
  }

  if (!job) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse-glow w-4 h-4 rounded-full bg-accent" />
      </div>
    );
  }

  const progress = job.total > 0 ? (job.generated / job.total) * 100 : 0;
  const isActive = ['running', 'paused', 'pending'].includes(job.status);

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link to="/" className="p-2 rounded-lg bg-bg-card hover:bg-bg-card-hover text-text-secondary">
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-text-primary">Job {job.id}</h1>
            <span className={`badge badge-${job.status}`}>{job.status}</span>
            {connected && streaming && (
              <span className="flex items-center gap-1 text-xs text-success">
                <div className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                Live
              </span>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {job.status === 'running' && (
            <button onClick={handlePause} className="p-2 rounded-lg bg-warning/10 text-warning hover:bg-warning/20">
              <Pause className="w-4 h-4" />
            </button>
          )}
          {job.status === 'paused' && (
            <button onClick={handleResume} className="p-2 rounded-lg bg-success/10 text-success hover:bg-success/20">
              <Play className="w-4 h-4" />
            </button>
          )}
          {isActive && (
            <button onClick={handleCancel} className="p-2 rounded-lg bg-danger/10 text-danger hover:bg-danger/20">
              <Square className="w-4 h-4" />
            </button>
          )}
          {job.status === 'completed' && (
            <a
              href={api.jobBundleUrl(job.id)}
              className="btn-glow flex items-center gap-2 text-sm"
            >
              <Download className="w-4 h-4" />
              Download All
            </a>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="glass-card p-5 mb-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-text-secondary">Progress</span>
          <span className="text-sm font-semibold text-accent-light">
            {job.generated}/{job.total}
          </span>
        </div>
        <div className="progress-track mb-3">
          <div
            className="progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-1 text-success">
            <CheckCircle className="w-3 h-3" /> {job.accepted} accepted
          </span>
          <span className="flex items-center gap-1 text-danger">
            <XCircle className="w-3 h-3" /> {job.failed} failed
          </span>
          <span className="flex items-center gap-1 text-warning">
            <RotateCcw className="w-3 h-3" /> {job.retried} retried
          </span>
          <span className="flex items-center gap-1 text-text-muted ml-auto">
            <Clock className="w-3 h-3" /> {Math.round(progress)}%
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Entries Grid */}
        <div className="lg:col-span-2">
          <h2 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Zap className="w-4 h-4 text-accent" />
            Generated Entries ({entries.length})
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3 max-h-[60vh] overflow-y-auto pr-1">
            {entries.map((entry) => (
              <Link
                key={entry.entry_num}
                to={entry.entry_id ? `/entry/${entry.entry_id}` : '#'}
                className={`glass-card p-3 group hover:scale-[1.02] transition-transform ${
                  entry.status === 'accepted' ? '' : 'opacity-60'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-text-primary">#{entry.global_id}</span>
                  <span className={`w-2 h-2 rounded-full ${
                    entry.status === 'accepted' ? 'bg-success' : 'bg-danger'
                  }`} />
                </div>
                {entry.title && (
                  <p className="text-xs text-text-secondary truncate mb-1">{entry.title}</p>
                )}
                <div className="flex items-center gap-1 text-[10px] text-text-muted">
                  <span>{entry.app_type?.replace('_', ' ')}</span>
                  <span>·</span>
                  <span>{entry.theme}</span>
                  {entry.word_count && (
                    <>
                      <span>·</span>
                      <span>{entry.word_count}w</span>
                    </>
                  )}
                </div>
                {entry.persona_summary && (
                  <div className="text-[10px] text-text-muted mt-0.5 truncate">
                    {entry.persona_summary}
                  </div>
                )}
              </Link>
            ))}
          </div>
        </div>

        {/* Live Log */}
        <div>
          <h2 className="text-sm font-semibold text-text-primary mb-3">Live Log</h2>
          <div className="glass-card p-3 h-[60vh] overflow-y-auto font-mono text-[11px] text-text-secondary space-y-0.5">
            {log.length === 0 ? (
              <p className="text-text-muted italic">Waiting for events...</p>
            ) : (
              log.map((l, i) => <div key={i}>{l}</div>)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
