import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api, ApiError, type ReviewItem } from '../api'
import { useAuth } from '../auth-context'
import { timeAgo } from '../time'

type Tab = 'pending' | 'rejected'

export default function Review() {
  const { user, loading } = useAuth()
  const [tab, setTab] = useState<Tab>('pending')
  const [items, setItems] = useState<ReviewItem[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const isAdmin = user?.is_admin ?? false

  useEffect(() => {
    if (!isAdmin) return
    setItems(null)
    setError(null)
    api.reviewQueue(tab).then(setItems).catch((e) => setError(e.message))
  }, [tab, isAdmin])

  if (loading) return null
  if (!user) return <Navigate to="/login" replace />
  if (!isAdmin) return <p className="muted">Only moderators can see the review queue.</p>

  async function decide(item: ReviewItem, decision: 'approve' | 'reject') {
    setBusy(item.id)
    setError(null)
    try {
      await api.decide(item.id, decision)
      // Either way it no longer belongs on this tab.
      setItems((list) => list && list.filter((i) => i.id !== item.id))
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Could not save decision')
    } finally {
      setBusy(null)
    }
  }

  return (
    <section>
      <h1>Review queue</h1>
      <div className="tabs">
        <button className={tab === 'pending' ? 'active' : ''} onClick={() => setTab('pending')}>
          Held for review
        </button>
        <button className={tab === 'rejected' ? 'active' : ''} onClick={() => setTab('rejected')}>
          Rejected
        </button>
      </div>

      {error && <p className="error">{error}</p>}
      {items === null && !error && <p className="muted">Loading…</p>}
      {items?.length === 0 && (
        <p className="muted">
          {tab === 'pending' ? 'Nothing waiting for review.' : 'Nothing has been rejected.'}
        </p>
      )}

      <ul className="list">
        {items?.map((item) => (
          <li key={item.id} className="card">
            <div className="meta">
              {item.kind === 'question' ? 'Question' : 'Answer'} by {item.author} ·{' '}
              {timeAgo(item.created_at)} · <strong>{item.reason}</strong>
              {item.reviewed_by && ` · last decided by ${item.reviewed_by}`}
            </div>
            {item.kind === 'answer' && (
              <div className="meta">
                On{' '}
                <Link to={`/q/${item.question_id}`} className="title">
                  {item.question_title}
                </Link>
              </div>
            )}
            {item.kind === 'question' && <p className="title">{item.question_title}</p>}
            {item.body && <p className="body">{item.body}</p>}
            {item.llm_verdict && (
              <p className="meta">
                Classifier said <strong>{item.llm_verdict}</strong>: {item.llm_reason}
              </p>
            )}
            <div className="actions">
              <button onClick={() => decide(item, 'approve')} disabled={busy === item.id}>
                Approve
              </button>
              {tab === 'pending' && (
                <button onClick={() => decide(item, 'reject')} disabled={busy === item.id}>
                  Reject
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
