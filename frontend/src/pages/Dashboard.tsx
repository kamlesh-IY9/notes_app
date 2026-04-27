/** Dashboard — shows job list, stats, and quick actions. */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type Job } from '../lib/api';
import {
  Zap, Plus, Download, Trash2, Clock, CheckCircle,
  XCircle, Play, Pause, BarChart3, Layers
} from 'lucide-react';

export default function Dashboard() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [jobsRes, settingsRes] = await Promise.all([
        api.listJobs(),
        api.getSettings(),
      ]);
      setJobs(jobsRes.jobs);
      setSettings(settingsRes);
    } catch (e) {
      console.error('Failed to load:', e);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(jobId: string) {
    if (!confirm('Delete this job and all its entries?')) return;
    await api.deleteJob(jobId);
    setJobs((prev) => prev.filter((j) => j.id !== jobId));
  }

  // Aggregate stats
  const totalGenerated = jobs.reduce((s, j) => s + j.generated, 0);
  const totalAccepted = jobs.reduce((s, j) => s + j.accepted, 0);
  const totalFailed = jobs.reduce((s, j) => s + j.failed, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse-glow w-4 h-4 rounded-full bg-accent" />
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* Hero Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple-500 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-accent-light bg-clip-text text-transparent">
            Notes Generator
          </h1>
        </div>
        <p className="text-text-secondary text-sm ml-[52px]">
          AI-powered People &amp; Relationships training data pipeline
        </p>
      </div>

      {/* Provider Status */}
      {settings && (
        <div className="glass-card p-4 mb-6 flex items-center gap-4 flex-wrap">
          <span className="text-xs text-text-muted font-semibold uppercase tracking-wider">Providers</span>
          {['groq', 'gemini', 'nim', 'openrouter', 'glm'].map((p) => {
            const ok = settings[`${p}_configured`];
            return (
              <div
                key={p}
                className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg ${
                  ok
                    ? 'bg-success/10 text-success'
                    : 'bg-danger/10 text-danger'
                }`}
              >
                <div className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-success' : 'bg-danger'}`} />
                {p.toUpperCase()}: {ok ? (settings as any)[`${p}_model`] : 'Not configured'}
              </div>
            );
          })}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {[
          { label: 'Total Jobs', value: jobs.length, icon: Layers, color: 'accent' },
          { label: 'Generated', value: totalGenerated, icon: BarChart3, color: 'accent-light' },
          { label: 'Accepted', value: totalAccepted, icon: CheckCircle, color: 'success' },
          { label: 'Failed', value: totalFailed, icon: XCircle, color: 'danger' },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="glass-card p-4 group">
            <div className="flex items-center gap-2 mb-2">
              <Icon className={`w-4 h-4 text-${color}`} />
              <span className="text-xs text-text-muted uppercase tracking-wide">{label}</span>
            </div>
            <div className={`text-2xl font-bold text-${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* New Job Button */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-semibold text-text-primary">Jobs</h2>
        <button
          onClick={() => navigate('/generate')}
          className="btn-glow flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          New Batch
        </button>
      </div>

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <div className="glass-card p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-bg-card mx-auto mb-4 flex items-center justify-center">
            <Zap className="w-8 h-8 text-text-muted" />
          </div>
          <h3 className="text-lg font-semibold mb-2">No jobs yet</h3>
          <p className="text-text-secondary text-sm mb-4">Create your first batch to start generating notes</p>
          <button onClick={() => navigate('/generate')} className="btn-glow text-sm">
            Create Batch
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {jobs.map((job) => (
            <JobCard
              key={job.id}
              job={job}
              onDelete={() => handleDelete(job.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function JobCard({ job, onDelete }: { job: Job; onDelete: () => void }) {
  const navigate = useNavigate();
  const progress = job.total > 0 ? (job.generated / job.total) * 100 : 0;
  const isActive = ['running', 'paused'].includes(job.status);

  return (
    <div
      onClick={() => navigate(isActive ? `/progress/${job.id}` : `/progress/${job.id}`)}
      className="glass-card p-5 block group animate-fade-in cursor-pointer"
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-semibold text-text-primary">
              Job {job.id}
            </span>
            <span className={`badge badge-${job.status}`}>
              {job.status === 'running' && <Play className="w-3 h-3" />}
              {job.status === 'paused' && <Pause className="w-3 h-3" />}
              {job.status === 'completed' && <CheckCircle className="w-3 h-3" />}
              {job.status === 'failed' && <XCircle className="w-3 h-3" />}
              {job.status}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-text-muted">
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(job.created_at).toLocaleDateString()}
            </span>
            <span>Batch: {job.batch_size}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {job.status === 'completed' && (
            <button
              onClick={(e) => { e.preventDefault(); e.stopPropagation(); window.open(api.jobBundleUrl(job.id), '_blank'); }}
              className="p-2 rounded-lg bg-bg-card hover:bg-bg-card-hover text-text-secondary hover:text-success transition-colors"
              title="Download Bundle"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={(e) => { e.preventDefault(); e.stopPropagation(); onDelete(); }}
            className="p-2 rounded-lg bg-bg-card hover:bg-danger/20 text-text-muted hover:text-danger transition-colors"
            title="Delete"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress */}
      <div className="progress-track mb-2">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>
      <div className="flex items-center justify-between text-xs text-text-muted">
        <span>{job.generated}/{job.total} generated</span>
        <div className="flex items-center gap-3">
          <span className="text-success">{job.accepted} ✓</span>
          <span className="text-danger">{job.failed} ✗</span>
          {job.retried > 0 && (
            <span className="text-warning">{job.retried} retried</span>
          )}
        </div>
      </div>
    </div>
  );
}
