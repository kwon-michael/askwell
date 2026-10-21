import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError, type QuestionDetail } from '../api'
import { useAuth } from '../auth-context'
import { ArrowLeft, Byline, ChevronUp } from '../ui'

export default function QuestionPage() {
  const id = Number(useParams().id)
  const { user } = useAuth()
  const [question, setQuestion] = useState<QuestionDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
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
    setNotice(null)
    try {
      const answer = await api.answer(id, draft)
      if (answer.status === 'published') {
        setQuestion((q) => q && { ...q, answers: [...q.answers, answer] })
        setDraft('')
      } else if (answer.status === 'pending') {
        setNotice('Thanks! Your answer is being reviewed and will appear once it’s approved.')
        setDraft('')
      } else {
        setError('Your answer was flagged by our spam filter and wasn’t posted.')
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not post answer')
    } finally {
      setPosting(false)
    }
  }

  const back = (
    <Link to="/" className="back">
      <ArrowLeft /> All questions
    </Link>
  )

  if (!question) {
    return (
      <div className="narrow">
        {back}
        {error ? (
          <div className="panel empty">
            <h3>Question not found</h3>
            <p>It may have been removed, or it’s still waiting for review.</p>
          </div>
        ) : (
          <p className="muted">Loading…</p>
        )}
      </div>
    )
  }

  const count = question.answers.length

  return (
    <article className="narrow">
      {back}

      <header className="question-head">
        <h1>{question.title}</h1>
        <Byline name={question.author} at={question.created_at} size={24} />
        {question.body && <p className="prose">{question.body}</p>}
      </header>

      <div className="section-head">
        <h2>
          {count} {count === 1 ? 'answer' : 'answers'}
        </h2>
        {count > 1 && <span className="faint">Ranked by votes and recency</span>}
      </div>

      {error && <p className="callout error">{error}</p>}

      {count > 0 ? (
        <ul className="rows panel">
          {question.answers.map((a) => {
            const own = user?.username === a.author
            return (
              <li key={a.id} className="answer">
                <button
                  className={`vote${a.voted_by_me ? ' voted' : ''}`}
                  onClick={() => vote(a.id)}
                  disabled={!user || own}
                  aria-pressed={a.voted_by_me}
                  aria-label={`Upvote (${a.votes})`}
                  title={!user ? 'Log in to vote' : own ? 'You can’t vote on your own answer' : undefined}
                >
                  <ChevronUp />
                  {a.votes}
                </button>
                <div>
                  <p className="prose">{a.body}</p>
                  <Byline name={a.author} at={a.created_at} size={20} />
                </div>
              </li>
            )
          })}
        </ul>
      ) : (
        <div className="panel empty">
          <h3>No answers yet</h3>
          <p>{user ? 'Know something useful? Be the first to answer.' : 'Log in to write the first answer.'}</p>
        </div>
      )}

      <section className="reply">
        {notice && (
          <p className="callout info" style={{ marginBottom: 14 }}>
            {notice}
          </p>
        )}
        {user ? (
          <form onSubmit={submit}>
            <h2>Your answer</h2>
            <div className="composer">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="Share what you know…"
                rows={5}
                aria-label="Your answer"
                required
              />
              <div className="composer-foot">
                <span>Be specific; plain text, line breaks are kept.</span>
                <button type="submit" className="primary" disabled={posting || !draft.trim()}>
                  {posting ? 'Posting…' : 'Post answer'}
                </button>
              </div>
            </div>
          </form>
        ) : (
          <div className="panel panel-pad" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <span className="muted">Log in to answer or vote.</span>
            <Link to="/login" className="button primary small">
              Log in
            </Link>
          </div>
        )}
      </section>
    </article>
  )
}
