import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, type QuestionSummary, type TopAnswer } from '../api'
import { useAuth } from '../auth-context'
import { Byline } from '../ui'

export default function Feed() {
  const { user } = useAuth()
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
    <>
      <div className="page-head">
        <div>
          <h1>Questions</h1>
          <p>Ask what you’re curious about, answer what you know, and upvote what helped.</p>
        </div>
      </div>

      <div className="layout">
        <section>
          <div className="toolbar">
            <div className="segmented" role="tablist" aria-label="Sort questions">
              <button
                role="tab"
                aria-selected={sort === 'new'}
                className={sort === 'new' ? 'active' : ''}
                onClick={() => setSort('new')}
              >
                Newest
              </button>
              <button
                role="tab"
                aria-selected={sort === 'active'}
                className={sort === 'active' ? 'active' : ''}
                onClick={() => setSort('active')}
              >
                Most answered
              </button>
            </div>
            {questions && questions.length > 0 && (
              <span className="faint">
                {questions.length} {questions.length === 1 ? 'question' : 'questions'}
              </span>
            )}
          </div>

          {error && <p className="callout error">{error}</p>}

          <div className="panel">
            {questions === null && !error && <p className="empty">Loading questions…</p>}
            {questions?.length === 0 && (
              <div className="empty">
                <h3>No questions yet</h3>
                <p>Be the first to ask something.</p>
                <Link to={user ? '/ask' : '/login'} className="button primary">
                  Ask a question
                </Link>
              </div>
            )}
            {questions && questions.length > 0 && (
              <ul className="rows">
                {questions.map((q) => (
                  <li key={q.id}>
                    <Link to={`/q/${q.id}`} className="question-row">
                      <div className={`count${q.answer_count > 0 ? ' has' : ''}`}>
                        <strong>{q.answer_count}</strong>
                        {q.answer_count === 1 ? 'answer' : 'answers'}
                      </div>
                      <div>
                        <p className="question-title">{q.title}</p>
                        <Byline name={q.author} at={q.created_at} size={20} />
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <aside className="sidebar">
          <div className="panel panel-pad">
            <p className="panel-title">Top answers this week</p>
            {top.length > 0 ? (
              <ol className="top-list">
                {top.map((t) => (
                  <li key={t.answer_id}>
                    <div>
                      <Link to={`/q/${t.question_id}`}>{t.question_title}</Link>
                      <div className="meta" style={{ marginTop: 4 }}>
                        {t.author}
                        <span className="dot" />
                        {t.votes} {t.votes === 1 ? 'upvote' : 'upvotes'}
                      </div>
                    </div>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="muted" style={{ margin: 0, fontSize: '0.9rem' }}>
                Answers upvoted in the last seven days show up here.
              </p>
            )}
          </div>

          <div className="panel panel-pad">
            <p className="panel-title">How it works</p>
            <ul className="steps">
              <li>Answers are ranked by votes, with a time decay so newer answers get a chance.</li>
              <li>New posts pass a spam filter; borderline ones are checked by Claude, then a human.</li>
              <li>You can’t vote on your own answers.</li>
            </ul>
          </div>
        </aside>
      </div>
    </>
  )
}
