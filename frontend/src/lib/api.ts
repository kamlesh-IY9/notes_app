/** API client — typed fetch wrappers for the Notes Generator backend. */

const BASE = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  return res.json();
}

// ── Types ────────────────────────────────────────────────

export interface Job {
  id: string;
  status: string;
  batch_size: number;
  config: string;
  created_at: string;
  updated_at: string;
  total: number;
  generated: number;
  accepted: number;
  rejected: number;
  failed: number;
  retried: number;
}

export interface Entry {
  id: string;
  job_id: string;
  entry_num: number;
  global_id: number;
  part_num: number;
  status: string;
  note_text: string;
  has_title: number;
  title: string | null;
  app_type: string;
  theme: string;
  connectivity: string;
  note_date: string;
  relationship: string;
  topic: string;
  mood: string;
  word_count: number;
  line_count: number;
  txt_filename: string;
  jpg_filename: string;
  validation_json: string;
  persona_json: string;
  validation?: Array<{ name: string; passed: boolean; detail: string }>;
  persona?: Record<string, unknown>;
}

export interface JobConfig {
  dataset_type: 'people_relationships' | 'contacts' | 'events' | 'topics_of_interest';
  batch_size: number;
  app_distribution: Record<string, number>;
  contact_app_distribution?: Record<string, number>;
  dark_mode_share: number;
  title_share: number;
  date_min: string;
  date_max: string;
  connectivity_distribution: Record<string, number>;
  start_global_id: number;
  start_part: number;
  language?: string;
}

export interface Settings {
  providers: string[];
  groq_configured: boolean;
  gemini_configured: boolean;
  nim_configured: boolean;
  groq_model: string;
  gemini_model: string;
  nim_model: string;
}

// ── Jobs ─────────────────────────────────────────────────

export const api = {
  // Jobs
  listJobs: () => request<{ jobs: Job[] }>('/jobs'),
  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  createJob: (config: JobConfig) =>
    request<{ job_id: string }>('/jobs', {
      method: 'POST',
      body: JSON.stringify(config),
    }),
  pauseJob: (id: string) => request(`/jobs/${id}/pause`, { method: 'POST' }),
  resumeJob: (id: string) => request(`/jobs/${id}/resume`, { method: 'POST' }),
  cancelJob: (id: string) => request(`/jobs/${id}/cancel`, { method: 'POST' }),
  deleteJob: (id: string) => request(`/jobs/${id}`, { method: 'DELETE' }),

  // Entries
  listEntries: (jobId: string, params?: Record<string, string>) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : '';
    return request<{ entries: Entry[]; total: number }>(`/entries/by-job/${jobId}${qs}`);
  },
  getEntry: (id: string) => request<Entry>(`/entries/${id}`),
  updateEntry: (id: string, data: { note_text?: string; status?: string }) =>
    request(`/entries/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Settings
  getSettings: () => request<Settings>('/settings'),
  testProvider: (provider: string) =>
    request<{ status: string; provider: string; response?: string; error?: string }>(
      '/settings/test-provider',
      { method: 'POST', body: JSON.stringify({ provider }) }
    ),

  // Download URLs
  entryTextUrl: (id: string) => `${BASE}/entries/${id}/text`,
  entryImageUrl: (id: string) => `${BASE}/entries/${id}/image`,
  entryBundleUrl: (id: string) => `${BASE}/entries/${id}/bundle.zip`,
  jobBundleUrl: (id: string, status = 'accepted') =>
    `${BASE}/jobs/${id}/bundle.zip?status=${status}`,

  // Health
  health: () => request<{ status: string }>('/health'),
};
