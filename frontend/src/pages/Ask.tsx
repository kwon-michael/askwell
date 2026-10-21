import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useAuth } from '../auth-context'

export default function Ask() {
  const { user, loading } = useAuth()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [posting, setPosting] = useState(false)

  if (loading) return null
  if (!user) return <Navigate to="/login" replace />

  async function submit(e: FormEvent) {
    e.preventDefault()
    setPosting(true)
    setError(null)
    try {
      const q = await api.ask(title, body)
      navigate(`/q/${q.id}`)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not post question')
      setPosting(false)
    }
  }

  return (
    <form onSubmit={submit} className="stack narrow">
      <h1>Ask a question</h1>
      <input
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="What do you want to know?"
        minLength={10}
        maxLength={200}
        required
      />
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Add details (optional)"
        rows={6}
      />
      {error && <p className="error">{error}</p>}
      <button type="submit" disabled={posting}>
        {posting ? 'Posting…' : 'Post question'}
      </button>
    </form>
  )
}
