/** Generate — simplified batch form. 3 size buttons, today's date, START. */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, type JobConfig } from '../lib/api';
import { Sparkles, ChevronRight } from 'lucide-react';

const TODAY = new Date().toISOString().slice(0, 10);
// Default date range: shuffle between April 24, 25, 26 (2026). The orchestrator
// picks a random day in [date_min, date_max] per note + random hour/minute.
const DEFAULT_DATE_MIN = "2026-04-24";
const DEFAULT_DATE_MAX = "2026-04-26";

const DEFAULT_CONFIG: JobConfig = {
  dataset_type: 'people_relationships',
  batch_size: 100,
  language: 'english',
  // MIUI-primary distribution (matches reference samples)
  app_distribution: { miui_notes: 70, apple_notes: 15, samsung_notes: 10, google_keep: 5 },
  contact_app_distribution: { miui_notes: 50, apple_notes: 30, samsung_notes: 12, google_keep: 8 },
  dark_mode_share: 25,
  title_share: 9,           // ~9% real titles, rest empty placeholder (matches samples)
  date_min: DEFAULT_DATE_MIN,
  date_max: DEFAULT_DATE_MAX,
  connectivity_distribution: {
    wifi_cellular: 60, cellular_only: 25, wifi_only: 10, no_service: 5,
  },
  start_global_id: 1100,
  start_part: 32,
};

export default function Generate() {
  const [config, setConfig] = useState<JobConfig>(DEFAULT_CONFIG);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  function setBatchSize(n: number) {
    setConfig((c) => ({ ...c, batch_size: n }));
  }

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const res = await api.createJob(config);
      navigate(`/progress/${res.job_id}`);
    } catch (e) {
      alert('Failed to create job: ' + (e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const sizeOptions = [10, 100, 1000];

  return (
    <div className="animate-fade-in max-w-xl mx-auto pt-8">
      {/* Header */}
      <div className="mb-10 text-center">
        <h1 className="text-3xl font-bold text-text-primary mb-2">Notes Generator</h1>
        <p className="text-sm text-text-secondary">
          People &amp; Relationships or Contacts — phone screenshots
        </p>
      </div>

      <div className="space-y-6">
        {/* Language selector */}
        <div className="glass-card p-6">
          <label className="block text-sm font-semibold text-text-primary mb-4">
            Language
          </label>
          <div className="grid grid-cols-1 gap-3">
            {[
              { id: 'english', label: 'English', sublabel: 'en_US · USA personas' },
              { id: 'hindi', label: 'Hindi — हिंदी', sublabel: 'hi_IN · Indian personas · Devanagari' },
              { id: 'arabic', label: 'Arabic — العربية', sublabel: 'ar_AE · Arab personas · RTL' },
            ].map((opt) => (
              <button
                key={opt.id}
                onClick={() => setConfig((c) => ({ ...c, language: opt.id }))}
                className={`min-h-[68px] rounded-lg px-3 py-3 text-left transition-all ${
                  config.language === opt.id
                    ? 'bg-accent text-white shadow-lg shadow-accent/30'
                    : 'bg-bg-card text-text-secondary hover:bg-bg-card-hover'
                }`}
              >
                <div className="text-sm font-semibold leading-tight">{opt.label}</div>
                <div className="text-xs font-normal opacity-75 mt-1">{opt.sublabel}</div>
              </button>
            ))}
          </div>
          {config.language === 'hindi' && (
            <p className="mt-3 text-xs text-text-muted">
              Notes generated in English first, then translated to Hindi Devanagari. Indian names, states &amp; topics used.
            </p>
          )}
          {config.language === 'arabic' && (
            <p className="mt-3 text-xs text-text-muted">
              Notes generated in English first, then translated to Arabic. Arab names &amp; Gulf/Arab topics used. RTL layout in screenshots.
            </p>
          )}
        </div>

        {/* Dataset type */}
        <div className="glass-card p-6">
          <label className="block text-sm font-semibold text-text-primary mb-4">
            What do you want to generate?
          </label>
          <div className="grid grid-cols-2 gap-3">
            {[
              { id: 'people_relationships', label: 'People & Relationships', hint: 'personal notes about people' },
              { id: 'contacts',             label: 'Contacts',               hint: 'name + phone / email' },
              { id: 'events',               label: 'Events',                 hint: 'calendar & meeting notes' },
              { id: 'topics_of_interest',   label: 'Topics of Interest',     hint: 'learning & expert notes' },
            ].map((option) => (
              <button
                key={option.id}
                onClick={() => setConfig((c) => ({ ...c, dataset_type: option.id as JobConfig['dataset_type'] }))}
                className={`min-h-[76px] rounded-lg px-3 py-3 text-left transition-all ${
                  config.dataset_type === option.id
                    ? 'bg-accent text-white shadow-lg shadow-accent/30'
                    : 'bg-bg-card text-text-secondary hover:bg-bg-card-hover'
                }`}
              >
                <div className="text-sm font-semibold leading-tight">{option.label}</div>
                <div className="text-xs font-normal opacity-75 mt-1">{option.hint}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Batch size — three big buttons */}
        <div className="glass-card p-6">
          <label className="block text-sm font-semibold text-text-primary mb-4">
            How many notes?
          </label>
          <div className="grid grid-cols-3 gap-3">
            {sizeOptions.map((n) => (
              <button
                key={n}
                onClick={() => setBatchSize(n)}
                className={`py-4 rounded-lg text-lg font-semibold transition-all ${
                  config.batch_size === n
                    ? 'bg-accent text-white shadow-lg shadow-accent/30'
                    : 'bg-bg-card text-text-secondary hover:bg-bg-card-hover'
                }`}
              >
                {n}
                <div className="text-xs font-normal opacity-70 mt-1">
                  {n === 10 ? 'smoke' : n === 100 ? 'test' : 'full'}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Date range — From / To */}
        <div className="glass-card p-6">
          <label className="block text-sm font-semibold text-text-primary mb-3">
            Date range
          </label>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-text-muted mb-1">From</p>
              <input
                type="date"
                value={config.date_min}
                max={config.date_max}
                onChange={(e) => setConfig((c) => ({ ...c, date_min: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-bg-card border border-border text-text-primary text-sm focus:border-accent focus:outline-none"
              />
            </div>
            <div>
              <p className="text-xs text-text-muted mb-1">To</p>
              <input
                type="date"
                value={config.date_max}
                min={config.date_min}
                max={TODAY}
                onChange={(e) => setConfig((c) => ({ ...c, date_max: e.target.value }))}
                className="w-full px-3 py-2 rounded-lg bg-bg-card border border-border text-text-primary text-sm focus:border-accent focus:outline-none"
              />
            </div>
          </div>
          <p className="mt-2 text-xs text-text-muted">
            Each note gets a random date + time within this range.
          </p>
        </div>

        {/* START button */}
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="btn-glow w-full py-4 text-lg font-semibold flex items-center justify-center gap-2 disabled:opacity-50"
        >
          {submitting ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Generate {config.batch_size} notes
              <ChevronRight className="w-4 h-4" />
            </>
          )}
        </button>

        <p className="text-center text-xs text-text-muted">
          Estimated time: ~{Math.ceil(config.batch_size * (config.dataset_type === 'contacts' ? 0.04 : 0.18))} min &middot; Output: {config.batch_size} .txt + {config.batch_size} .jpg
        </p>
      </div>
    </div>
  );
}
