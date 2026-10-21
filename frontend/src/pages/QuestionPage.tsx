import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError, type QuestionDetail } from '../api'
import { useAuth } from '../auth-context'
import { timeAgo } from '../time'

export default function QuestionPage() {
  const id = Number(useParams().id)
  const { user } = useAuth()
  const [question, setQuestion] = useState<QuestionDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [posting, setPosting] = useState(false)

  useEffect(() => {
    api.question(id).then(setQuestion).catch((e) => setError(e.message))
    // Reload when the user logs in or out so voted_by_me is correct.
  }, [id, user])

  async function vote(answerId: number) {
    try {
      const result = await api.vote(answerId)
      setQuestion((q) =>
        q && {
          ...q,
          answers: q.answers.map((a) =>
            a.id === answerId ? { ...a, votes: result.votes, voted_by_me: result.voted_by_me } : a,
          ),
        },
      )
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Vote failed')
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    setPosting(true)
    setError(null)
    try {
      const answer = await api.answer(id, draft)
      setQuestion((q) => q && { ...q, answers: [...q.answers, answer] })
      setDraft('')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not post answer')
    } finally {
      setPosting(false)
    }
  }

  if (!question) return error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>

  return (
    <article>
      <h1>{question.title}</h1>
      <div className="meta">
        Asked by {question.author} · {timeAgo(question.created_at)}
      </div>
      {question.body && <p className="body">{question.body}</p>}

      <h2>
        {question.answers.length} {question.answers.length === 1 ? 'answer' : 'answers'}
      </h2>
      {error && <p className="error">{error}</p>}

      <ul className="list">
        {question.answers.map((a) => (
          <li key={a.id} className="card answer">
            <button
              className={`vote ${a.voted_by_me ? 'voted' : ''}`}
              onClick={() => vote(a.id)}
              disabled={!user || user.username === a.author}
              title={!user ? 'Log in to vote' : undefined}
            >
              ▲ {a.votes}
            </button>
            <div>
              <p className="body">{a.body}</p>
              <div className="meta">
                {a.author} · {timeAgo(a.created_at)}
              </div>
            </div>
          </li>
        ))}
      </ul>

      {user ? (
        <form onSubmit={submit} className="stack">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Write your answer"
            rows={6}
            required
          />
          <button type="submit" disabled={posting || !draft.trim()}>
            {posting ? 'Posting…' : 'Post answer'}
          </button>
        </form>
      ) : (
        <p className="muted">
          <Link to="/login">Log in</Link> to answer.
        </p>
      )}
    </article>
  )
}
