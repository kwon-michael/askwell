import { useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api'
import { useAuth } from '../auth-context'

export default function Login() {
  const { login, register } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [mode, setMode] = useState<'login' | 'register'>(
    params.get('mode') === 'register' ? 'register' : 'login',
  )
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await (mode === 'login' ? login : register)(username, password)
      navigate('/')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Something went wrong')
      setBusy(false)
    }
  }

  const registering = mode === 'register'

  return (
    <div className="narrower">
      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <h1>{registering ? 'Create your account' : 'Welcome back'}</h1>
        <p className="lede" style={{ margin: '8px auto 0' }}>
          {registering ? 'Join to ask, answer, and vote.' : 'Log in to ask, answer, and vote.'}
        </p>
      </div>

      <form onSubmit={submit} className="panel panel-pad stack" style={{ padding: 24 }}>
        <label className="field">
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
            required
          />
        </label>
        <label className="field">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={registering ? 'At least 8 characters' : undefined}
            autoComplete={registering ? 'new-password' : 'current-password'}
            required
          />
        </label>
        {error && <p className="callout error">{error}</p>}
        <button type="submit" className="primary block" disabled={busy}>
          {busy ? 'One moment…' : registering ? 'Create account' : 'Log in'}
        </button>
      </form>

      <p className="muted" style={{ textAlign: 'center', marginTop: 18, fontSize: '0.92rem' }}>
        {registering ? 'Already have an account?' : 'New here?'}{' '}
        <button
          type="button"
          className="text-button"
          style={{ color: 'var(--accent-text)', fontWeight: 500 }}
          onClick={() => {
            setMode(registering ? 'login' : 'register')
            setError(null)
          }}
        >
          {registering ? 'Log in' : 'Create an account'}
        </button>
      </p>
    </div>
  )
}
