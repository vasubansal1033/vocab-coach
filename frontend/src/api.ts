export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
    ...init,
  })
  if (response.status === 401) {
    window.location.href = '/auth/login'
    throw new ApiError(401, 'Not authenticated')
  }
  if (!response.ok) {
    const detail = await response.text()
    throw new ApiError(response.status, detail || response.statusText)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export type User = {
  id: string
  display_name: string | null
  email: string | null
}

export type Conversation = {
  id: string
  title: string
  feedback_expectations?: string | null
  flow_mode?: boolean
  allow_idioms?: boolean
  created_at: string | null
  messages?: Message[]
}

export type Recap = {
  words_to_keep: { word: string; option_id: string | null; source: string }[]
  crutch_words: { lemma: string; count: number }[]
  rewrite_sentence: string | null
}

export type Message = {
  id: string
  role: 'user' | 'partner' | string
  content: string
  created_at: string | null
}

export type Suggestion = {
  id: string
  original_text: string
  span_start: number
  span_end: number
  question: string | null
  why: string | null
  options: { id: string; word: string; meaning: string }[]
}

export type FeedbackPayload = {
  failed: boolean
  content?: string
  overview?: string | null
  highlighted_html?: string
  keep?: string[]
  suggestions: Suggestion[]
}

export type Dashboard = {
  window_start: string
  window_end: string
  crutch_rate: number | null
  weekly: { label: string; rate: number | null }[]
  overuse: {
    word: string
    uses: number
    lift: number
    groups: { id: string; sense_gloss: string }[]
  }[]
  acceptance: number | null
  spontaneous: number | null
  misuse: number | null
  drill_weeks: { label: string; score: number | null }[]
  mtld: number | null
}

export type Account = {
  user: User
  limits: {
    llm_calls_24h: number
    llm_call_limit_per_day: number
    llm_cost_usd_24h: number
    llm_cost_limit_usd_per_day: number
  }
  privacy_note: string
}

export const api = {
  me: () => request<User>('/api/me'),
  account: () => request<Account>('/api/account'),
  deleteAccount: () => request<void>('/api/account/delete', { method: 'POST' }),
  conversations: () => request<{ conversations: Conversation[] }>('/api/conversations'),
  createConversation: (
    name: string,
    feedbackExpectations?: string,
    opts?: { flowMode?: boolean; allowIdioms?: boolean },
  ) =>
    request<Conversation>('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({
        name,
        feedback_expectations: feedbackExpectations?.trim() || null,
        flow_mode: opts?.flowMode ?? false,
        allow_idioms: opts?.allowIdioms ?? false,
      }),
    }),
  deleteConversation: (id: string) =>
    request<void>(`/api/conversations/${id}`, { method: 'DELETE' }),
  conversation: (id: string) => request<Conversation>(`/api/conversations/${id}`),
  postMessage: (id: string, content: string) =>
    request<Message>(`/api/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    }),
  feedback: (conversationId: string, messageId: string) =>
    request<FeedbackPayload>(
      `/api/conversations/${conversationId}/messages/${messageId}/feedback`,
    ),
  accept: (conversationId: string, suggestionId: string, optionId: string) =>
    request<{ dismissed: boolean; accepted_word: string; original_text: string }>(
      `/api/conversations/${conversationId}/suggestions/${suggestionId}/accept`,
      { method: 'POST', body: JSON.stringify({ option_id: optionId }) },
    ),
  dismiss: (conversationId: string, suggestionId: string) =>
    request<{ dismissed: boolean; original_text: string }>(
      `/api/conversations/${conversationId}/suggestions/${suggestionId}/dismiss`,
      { method: 'POST' },
    ),
  retry: (conversationId: string, suggestionId: string, optionId: string) =>
    request<{ text: string }>(
      `/api/conversations/${conversationId}/suggestions/${suggestionId}/retry`,
      { method: 'POST', body: JSON.stringify({ option_id: optionId }) },
    ),
  recap: (conversationId: string) =>
    request<Recap>(`/api/conversations/${conversationId}/recap`),
  dashboard: (params?: { prompt_version?: string; model?: string }) => {
    const q = new URLSearchParams()
    if (params?.prompt_version) q.set('prompt_version', params.prompt_version)
    if (params?.model) q.set('model', params.model)
    const suffix = q.toString() ? `?${q}` : ''
    return request<Dashboard>(`/api/dashboard${suffix}`)
  },
  lemma: (lemma: string) =>
    request<{
      lemma: string
      weekly: { label: string; rate: number | null }[]
      options: { option_id: string; word: string; uses: number; correct_uses: number }[]
    }>(`/api/dashboard/lemma/${encodeURIComponent(lemma)}`),
  review: () =>
    request<{
      option: {
        id: string
        word: string
        distinction: string
        example: string
        cloze: string
      } | null
    }>('/api/review'),
  rateReview: (optionId: string, rating: string, answer: string) =>
    request<{ status: string }>(`/api/review/${optionId}`, {
      method: 'POST',
      body: JSON.stringify({ rating, answer }),
    }),
  createDrill: () =>
    request<{
      id: string
      vague_sentence: string
      intended_word: string
      context: string | null
      intended_distinction: string | null
    }>('/api/drills', {
      method: 'POST',
    }),
  drillHint: (drillId: string, level: 1 | 2 | 3) =>
    request<{ level: number; text: string }>(`/api/drills/${drillId}/hint?level=${level}`),
  gradeDrill: (drillId: string, answer: string, hintsUsed: number) =>
    request<{
      id: string
      answer: string
      score: number
      grade: Record<string, unknown>
      hints_used: number
    }>(`/api/drills/${drillId}/attempt`, {
      method: 'POST',
      body: JSON.stringify({ answer, hints_used: hintsUsed }),
    }),
  disputeDrillAttempt: (attemptId: string, note: string | null) =>
    request<{ status: string }>(`/api/drills/attempts/${attemptId}/dispute`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  drillSummary: (attemptIds: string[]) =>
    request<{
      mean_score: number
      words_practised: string[]
      total_hints_used: number
    }>(`/api/drills/summary?attempt_ids=${encodeURIComponent(attemptIds.join(','))}`),
}
