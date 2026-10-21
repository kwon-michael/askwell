import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './AuthProvider'
import { useAuth } from './auth-context'
import Ask from './pages/Ask'
import Feed from './pages/Feed'
import Login from './pages/Login'
import QuestionPage from './pages/QuestionPage'
import Review from './pages/Review'
import { Avatar } from './ui'

function Header() {
  const { user, logout } = useAuth()
  const navClass = ({ isActive }: { isActive: boolean }) => `nav-link${isActive ? ' active' : ''}`
  return (
    <header className="site-header">
      <div className="inner">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            A
          </span>
          Askwell
        </Link>
        <nav className="nav">
          {user ? (
            <>
              {user.is_admin && (
                <NavLink to="/review" className={navClass}>
                  Review
                </NavLink>
              )}
              <span className="user-chip">
                <Avatar name={user.username} size={26} />
                <span className="name">{user.username}</span>
              </span>
              <button className="text-button" onClick={logout}>
                Log out
              </button>
              <Link to="/ask" className="button primary small">
                Ask<span className="wide-only"> a question</span>
              </Link>
            </>
          ) : (
            <>
              <NavLink to="/login" className={navClass}>
                Log in
              </NavLink>
              <Link to="/login?mode=register" className="button primary small">
                Sign up
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}

function NotFound() {
  return (
    <div className="panel empty narrow">
      <h3>Page not found</h3>
      <p>That page doesn’t exist, or it may have been removed.</p>
      <Link to="/" className="button">
        Back to questions
      </Link>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Header />
        <main>
          <Routes>
            <Route path="/" element={<Feed />} />
            <Route path="/q/:id" element={<QuestionPage />} />
            <Route path="/ask" element={<Ask />} />
            <Route path="/login" element={<Login />} />
            <Route path="/review" element={<Review />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <footer className="site-footer">
          <div className="inner">
            Askwell · a small Q&amp;A community built with FastAPI, PostgreSQL and React
          </div>
        </footer>
      </BrowserRouter>
    </AuthProvider>
  )
}
