import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type QuestionSummary, type TopAnswer } from '../api'
import { timeAgo } from '../time'

export default function Feed() {
  const [sort, setSort] = useState<'new' | 'active'>('new')
  const [questions, setQuestions] = useState<QuestionSummary[] | null>(null)
  const [top, setTop] = useState<TopAnswer[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setQuestions(null)
    api.questions(sort).then(setQuestions).catch((e) => setError(e.message))
  }, [sort])

  useEffect(() => {
    api.topAnswers().then(setTop).catch(() => {})
  }, [])

  return (
    <div className="layout">
      <section>
        <div className="tabs">
          <button className={sort === 'new' ? 'active' : ''} onClick={() => setSort('new')}>
            Newest
          </button>
          <button className={sort === 'active' ? 'active' : ''} onClick={() => setSort('active')}>
            Most answered
          </button>
        </div>

        {error && <p className="error">{error}</p>}
        {questions === null && !error && <p className="muted">Loading…</p>}
        {questions?.length === 0 && (
          <p className="muted">
            No questions yet. <Link to="/ask">Ask the first one.</Link>
          </p>
        )}

        <ul className="list">
          {questions?.map((q) => (
            <li key={q.id} className="card">
              <Link to={`/q/${q.id}`} className="title">
                {q.title}
              </Link>
              <div className="meta">
                {q.author} · {timeAgo(q.created_at)} · {q.answer_count}{' '}
                {q.answer_count === 1 ? 'answer' : 'answers'}
              </div>
            </li>
          ))}
        </ul>
      </section>

      {top.length > 0 && (
        <aside>
          <h3>Top answers this week</h3>
          <ol className="top">
            {top.map((t) => (
              <li key={t.answer_id}>
                <Link to={`/q/${t.question_id}`}>{t.question_title}</Link>
                <div className="meta">
                  {t.author} · {t.votes} {t.votes === 1 ? 'upvote' : 'upvotes'}
                </div>
              </li>
            ))}
          </ol>
        </aside>
      )}
    </div>
  )
}
