import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api, ApiError, type ReviewItem } from '../api'
import { useAuth } from '../auth-context'
import { Byline } from '../ui'

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
  if (!isAdmin) {
    return (
      <div className="panel empty narrow">
        <h3>Moderators only</h3>
        <p>The review queue is only visible to moderators.</p>
      </div>
    )
  }

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
    <section className="narrow">
      <div className="page-head">
        <div>
          <h1>Review queue</h1>
          <p>Posts the spam filter held, or rejected, waiting on a human decision.</p>
        </div>
      </div>

      <div className="toolbar">
        <div className="segmented" role="tablist" aria-label="Review queue">
          <button
            role="tab"
            aria-selected={tab === 'pending'}
            className={tab === 'pending' ? 'active' : ''}
            onClick={() => setTab('pending')}
          >
            Held for review
          </button>
          <button
            role="tab"
            aria-selected={tab === 'rejected'}
            className={tab === 'rejected' ? 'active' : ''}
            onClick={() => setTab('rejected')}
          >
            Rejected
          </button>
        </div>
        {items && items.length > 0 && <span className="faint">{items.length} waiting</span>}
      </div>

      {error && <p className="callout error">{error}</p>}

      <div className="panel">
        {items === null && !error && <p className="empty">Loading…</p>}
        {items?.length === 0 && (
          <div className="empty">
            <h3>{tab === 'pending' ? 'All caught up' : 'Nothing rejected'}</h3>
            <p style={{ margin: 0 }}>
              {tab === 'pending'
                ? 'Nothing is waiting for review.'
                : 'Posts the filter rejects show up here, so you can overturn mistakes.'}
            </p>
          </div>
        )}
        {items && items.length > 0 && (
          <ul className="rows">
            {items.map((item) => (
              <li key={item.id} className="review-item">
                <div className="meta">
                  <span className="badge">{item.kind === 'question' ? 'Question' : 'Answer'}</span>
                  <span className="badge accent">{item.reason}</span>
                </div>

                {item.kind === 'answer' ? (
                  <p className="muted" style={{ margin: 0, fontSize: '0.9rem' }}>
                    On{' '}
                    <Link to={`/q/${item.question_id}`} className="serif">
                      {item.question_title}
                    </Link>
                  </p>
                ) : (
                  <p className="item-title">{item.question_title}</p>
                )}
                {item.body && <p className="prose">{item.body}</p>}

                {item.llm_verdict && (
                  <p className="classifier-note" style={{ margin: 0 }}>
                    Classifier said <strong>{item.llm_verdict}</strong>: {item.llm_reason}
                  </p>
                )}

                <div className="meta" style={{ justifyContent: 'space-between' }}>
                  <span className="meta">
                    <Byline name={item.author} at={item.created_at} size={20} />
                    {item.reviewed_by && (
                      <>
                        <span className="dot" />
                        last decided by {item.reviewed_by}
                      </>
                    )}
                  </span>
                  <span className="actions">
                    {tab === 'pending' && (
                      <button className="small" onClick={() => decide(item, 'reject')} disabled={busy === item.id}>
                        Reject
                      </button>
                    )}
                    <button className="small primary" onClick={() => decide(item, 'approve')} disabled={busy === item.id}>
                      Approve
                    </button>
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
