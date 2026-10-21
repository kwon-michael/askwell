import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth-context'
import { ArrowLeft } from '../ui'

const TITLE_MIN = 10

export default function Ask() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [posting, setPosting] = useState(false)

  if (loading) return null
  if (!user) return <Navigate to="/login" replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setPosting(true)
    setError(null)
    setNotice(null)
    try {
      const q = await api.ask(title, body)
      if (q.status === 'published') {
        navigate(`/q/${q.id}`)
        return
      }
      if (q.status === 'pending') {
        setNotice('Thanks! Your question is being reviewed and will appear once it’s approved.')
        setTitle('')
        setBody('')
      } else {
        setError('Your question was flagged by our spam filter and wasn’t posted.')
      }
      setPosting(false)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not post question')
      setPosting(false)
    }
  }

  const short = title.trim().length < TITLE_MIN

  return (
    <div className="narrow">
      <Link to="/" className="back">
        <ArrowLeft /> All questions
      </Link>
      <h1>Ask a question</h1>
      <p className="lede">A clear, specific title gets better answers. Add details if they help.</p>

      <form onSubmit={submit} className="stack" style={{ marginTop: 24 }}>
        {notice && <p className="callout info">{notice}</p>}
        {error && <p className="callout error">{error}</p>}
        <div className="composer">
          <input
            className="title-input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What do you want to know?"
            aria-label="Question title"
            minLength={TITLE_MIN}
            maxLength={200}
            required
            autoFocus
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Add context: what you’ve tried, what you expected (optional)"
            aria-label="Details"
            rows={6}
          />
          <div className="composer-foot">
            <span>{short ? `Title needs at least ${TITLE_MIN} characters` : `${title.length}/200`}</span>
            <button type="submit" className="primary" disabled={posting || short}>
              {posting ? 'Posting…' : 'Post question'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
