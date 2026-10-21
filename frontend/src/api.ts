const BASE = import.meta.env.VITE_API_URL ?? '/api'
const TOKEN_KEY = 'askwell_token'

export type ContentStatus = 'pending' | 'published' | 'rejected'

export type QuestionSummary = {
  id: number
  title: string
  author: string
  created_at: string
  answer_count: number
  status: ContentStatus
}

export type Answer = {
  id: number
  body: string
  author: string
  created_at: string
  votes: number
  voted_by_me: boolean
  status: ContentStatus
}

export type QuestionDetail = {
  id: number
  title: string
  body: string
  author: string
  created_at: string
  answers: Answer[]
}

export type VoteResult = { answer_id: number; votes: number; voted_by_me: boolean }

export type TopAnswer = {
  answer_id: number
  question_id: number
  question_title: string
  author: string
  votes: number
}

export type User = { id: number; username: string; is_admin: boolean }

export type ReviewItem = {
  id: number
  kind: 'question' | 'answer'
  question_id: number
  question_title: string
  body: string
  author: string
  reason: string
  status: ContentStatus
  created_at: string
  reviewed_by: string | null
  decided_at: string | null
  llm_verdict: 'allow' | 'remove' | 'unsure' | null
  llm_reason: string | null
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  const token = tokenStore.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    // FastAPI returns a string for HTTPException and a list for validation errors.
    const detail = data?.detail
    const message = Array.isArray(detail) ? detail[0]?.msg : detail
    throw new ApiError(res.status, message ?? res.statusText)
  }
  return res.json()
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const api = {
  register: (username: string, password: string) =>
    post<{ access_token: string }>('/auth/register', { username, password }),
  login: (username: string, password: string) =>
    post<{ access_token: string }>('/auth/login', { username, password }),
  me: () => request<User>('/auth/me'),

  questions: (sort: 'new' | 'active') => request<QuestionSummary[]>(`/questions?sort=${sort}`),
  question: (id: number) => request<QuestionDetail>(`/questions/${id}`),
  ask: (title: string, body: string) => post<QuestionSummary>('/questions', { title, body }),

  answer: (questionId: number, body: string) =>
    post<Answer>(`/questions/${questionId}/answers`, { body }),
  vote: (answerId: number) => post<VoteResult>(`/answers/${answerId}/vote`),

  reviewQueue: (status: 'pending' | 'rejected') =>
    request<ReviewItem[]>(`/moderation/queue?status=${status}`),
  decide: (reviewId: number, decision: 'approve' | 'reject') =>
    post<ReviewItem>(`/moderation/reviews/${reviewId}`, { decision }),
  topAnswers: () => request<TopAnswer[]>('/answers/top'),
}
