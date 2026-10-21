import { BrowserRouter, Link, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './AuthProvider'
import { useAuth } from './auth-context'
import Ask from './pages/Ask'
import Feed from './pages/Feed'
import Login from './pages/Login'
import QuestionPage from './pages/QuestionPage'

function Header() {
  const { user, logout } = useAuth()
  return (
    <header>
      <Link to="/" className="brand">
        Askwell
      </Link>
      <nav>
        {user ? (
          <>
            <Link to="/ask" className="button">
              Ask
            </Link>
            <span className="muted">{user.username}</span>
            <button className="link" onClick={logout}>
              Log out
            </button>
          </>
        ) : (
          <Link to="/login">Log in</Link>
        )}
      </nav>
    </header>
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
            <Route path="*" element={<p className="muted">Page not found.</p>} />
          </Routes>
        </main>
      </BrowserRouter>
    </AuthProvider>
  )
}
