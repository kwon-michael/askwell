import { useEffect, useState, type ReactNode } from 'react'
import { api, tokenStore, type User } from './api'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(() => tokenStore.get() !== null)

  useEffect(() => {
    if (!tokenStore.get()) return
    api
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false))
  }, [])

  async function acceptToken(token: string) {
    tokenStore.set(token)
    setUser(await api.me())
  }

  const value = {
    user,
    loading,
    login: async (username: string, password: string) =>
      acceptToken((await api.login(username, password)).access_token),
    register: async (username: string, password: string) =>
      acceptToken((await api.register(username, password)).access_token),
    logout: () => {
      tokenStore.clear()
      setUser(null)
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
