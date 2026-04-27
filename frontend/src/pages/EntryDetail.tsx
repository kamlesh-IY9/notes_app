/** EntryDetail — side-by-side note text + screenshot preview with validation. */

import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, type Entry } from '../lib/api';
import {
  ArrowLeft, CheckCircle, XCircle, User,
  FileText, Image, Package, Smartphone, Moon, Sun,
  Wifi, Calendar, Edit3
} from 'lucide-react';

export default function EntryDetail() {
  const { entryId } = useParams<{ entryId: string }>();
  const [entry, setEntry] = useState<Entry | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState('');

  useEffect(() => {
    if (!entryId) return;
    loadEntry();
  }, [entryId]);

  async function loadEntry() {
    if (!entryId) return;
    try {
      const e = await api.getEntry(entryId);
      setEntry(e);
      setEditText(e.note_text || '');
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    if (!entryId) return;
    await api.updateEntry(entryId, { note_text: editText });
    setEditing(false);
    loadEntry();
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse-glow w-4 h-4 rounded-full bg-accent" />
      </div>
    );
  }

  if (!entry) {
    return <div className="text-center text-text-muted py-20">Entry not found</div>;
  }

  const validation = entry.validation || [];
  const persona = entry.persona || {};
  const passedChecks = validation.filter((c) => c.passed).length;
  const totalChecks = validation.length;

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          to={`/progress/${entry.job_id}`}
          className="p-2 rounded-lg bg-bg-card hover:bg-bg-card-hover text-text-secondary"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-text-primary">
              Entry #{entry.global_id}
            </h1>
            <span className={`badge badge-${entry.status}`}>{entry.status}</span>
          </div>
          <p className="text-xs text-text-muted">{entry.txt_filename}</p>
        </div>
        <div className="flex items-center gap-2">
          <a
            href={api.entryTextUrl(entry.id)}
            className="p-2 rounded-lg bg-bg-card hover:bg-bg-card-hover text-text-secondary"
            title="Download .txt"
          >
            <FileText className="w-4 h-4" />
          </a>
          <a
            href={api.entryImageUrl(entry.id)}
            className="p-2 rounded-lg bg-bg-card hover:bg-bg-card-hover text-text-secondary"
            title="Download .jpg"
          >
            <Image className="w-4 h-4" />
          </a>
          <a
            href={api.entryBundleUrl(entry.id)}
            className="btn-glow flex items-center gap-2 text-sm"
          >
            <Package className="w-4 h-4" />
            Bundle
          </a>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Left: Note Text */}
        <div className="space-y-4">
          <div className="glass-card p-5">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                Note Text
              </h2>
              <button
                onClick={() => setEditing(!editing)}
                className={`p-1.5 rounded-lg text-xs flex items-center gap-1 ${
                  editing ? 'bg-accent text-white' : 'bg-bg-card text-text-secondary hover:bg-bg-card-hover'
                }`}
              >
                <Edit3 className="w-3 h-3" />
                {editing ? 'Editing' : 'Edit'}
              </button>
            </div>

            {editing ? (
              <div>
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={8}
                  className="w-full px-3 py-2 rounded-lg bg-bg-secondary border border-border text-text-primary text-sm font-mono focus:border-accent focus:outline-none resize-y"
                />
                <div className="flex justify-end gap-2 mt-2">
                  <button
                    onClick={() => { setEditing(false); setEditText(entry.note_text || ''); }}
                    className="px-3 py-1.5 rounded-lg bg-bg-card text-text-secondary text-xs"
                  >
                    Cancel
                  </button>
                  <button onClick={handleSave} className="btn-glow text-xs px-4 py-1.5">
                    Save
                  </button>
                </div>
              </div>
            ) : (
              <pre className="text-sm text-text-primary font-mono whitespace-pre-wrap leading-relaxed bg-bg-secondary rounded-lg p-4">
                {entry.note_text}
              </pre>
            )}

            <div className="flex items-center gap-3 mt-3 text-xs text-text-muted">
              <span>{entry.word_count} words</span>
              <span>{entry.line_count} lines</span>
              <span>{entry.has_title ? '📝 Has title' : '📄 No title'}</span>
            </div>
          </div>

          {/* Persona */}
          <div className="glass-card p-5">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2 mb-3">
              <User className="w-4 h-4 text-accent" />
              Persona (Internal)
            </h2>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {[
                ['Name', (persona as any).full_name],
                ['Age', `${(persona as any).age} (${(persona as any).age_bracket})`],
                ['Gender', (persona as any).gender],
                ['State', (persona as any).state],
                ['Occupation', (persona as any).occupation],
                ['Ethnicity', (persona as any).ethnicity],
                ['Relationship', entry.relationship],
                ['Topic', entry.topic],
                ['Mood', entry.mood],
              ].map(([label, value]) => (
                <div key={label as string} className="flex gap-2">
                  <span className="text-text-muted">{label}:</span>
                  <span className="text-text-secondary">{value || '—'}</span>
                </div>
              ))}
            </div>
            {(persona as any).voice_quirks?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {((persona as any).voice_quirks as string[]).map((q) => (
                  <span key={q} className="px-2 py-0.5 rounded-md bg-accent/10 text-accent text-[10px]">
                    {q}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Screenshot + Validation */}
        <div className="space-y-4">
          {/* Screenshot Preview */}
          <div className="glass-card p-5">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2 mb-3">
              <Image className="w-4 h-4 text-accent" />
              Screenshot
            </h2>
            <div className="flex justify-center">
              <img
                src={api.entryImageUrl(entry.id)}
                alt={`Screenshot for entry ${entry.global_id}`}
                className="entry-thumb max-h-[500px] w-auto"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                }}
              />
            </div>
            <div className="flex items-center justify-center gap-3 mt-3 text-xs text-text-muted">
              <span className="flex items-center gap-1">
                <Smartphone className="w-3 h-3" />
                {entry.app_type?.replace('_', ' ')}
              </span>
              <span className="flex items-center gap-1">
                {entry.theme === 'dark' ? <Moon className="w-3 h-3" /> : <Sun className="w-3 h-3" />}
                {entry.theme}
              </span>
              <span className="flex items-center gap-1">
                <Wifi className="w-3 h-3" />
                {entry.connectivity?.replace('_', ' ')}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {entry.note_date ? new Date(entry.note_date).toLocaleDateString() : '—'}
              </span>
            </div>
          </div>

          {/* Validation */}
          <div className="glass-card p-5">
            <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2 mb-3">
              <CheckCircle className="w-4 h-4 text-accent" />
              Validation ({passedChecks}/{totalChecks})
            </h2>
            <div className="space-y-1.5">
              {validation.map((check, i) => (
                <div
                  key={i}
                  className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${
                    check.passed
                      ? 'bg-success/5 text-success'
                      : 'bg-danger/10 text-danger'
                  }`}
                >
                  {check.passed ? (
                    <CheckCircle className="w-3 h-3 flex-shrink-0" />
                  ) : (
                    <XCircle className="w-3 h-3 flex-shrink-0" />
                  )}
                  <span className="font-medium">{check.name.replace(/_/g, ' ')}</span>
                  {check.detail && (
                    <span className="text-text-muted ml-auto truncate max-w-[200px]">
                      {check.detail}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
