import { useState } from 'react'
import type { FormEvent } from 'react'
import { registerUser, loginUser } from '../lib/api'

export function AuthPanel({ onAuthenticated, errorMessage }: { onAuthenticated: () => void; errorMessage: string | null }) {
  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [generatedPassword, setGeneratedPassword] = useState<string | null>(null)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [message, setMessage] = useState<string | null>(errorMessage)

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    try {
      const result = await registerUser(registerName, registerEmail)
      setGeneratedPassword(result.password)
      setLoginEmail(registerEmail)
      setLoginPassword(result.password)
      setMessage('Registration successful. Use the generated password to log in.')
    } catch (err) {
      console.error(err)
      setMessage('Registration failed. Email may already be in use.')
    }
  }

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    try {
      await loginUser(loginEmail, loginPassword)
      setMessage(null)
      onAuthenticated()
    } catch (err) {
      console.error(err)
      setMessage('Login failed. Check your credentials.')
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-warroom-blue px-4 text-slate-100">
      <div className="grid w-full max-w-3xl gap-6 rounded-lg border border-slate-700 bg-slate-900/70 p-6 shadow-lg shadow-warroom-cyan/10 md:grid-cols-2">
        <div>
          <h2 className="font-pixel text-warroom-cyan">Register</h2>
          <p className="text-xs text-slate-400">Enter your name and email to get a password.</p>
          <form className="mt-3 space-y-3" onSubmit={handleRegister}>
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Display name" value={registerName} onChange={(e) => setRegisterName(e.target.value)} required />
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Email" type="email" value={registerEmail} onChange={(e) => setRegisterEmail(e.target.value)} required />
            <button className="w-full rounded border border-slate-600 bg-warroom-cyan/20 py-2 text-xs font-bold tracking-wide text-warroom-cyan" type="submit">Register</button>
          </form>
          {generatedPassword && (
            <div className="mt-3 rounded border border-slate-600 bg-warroom-blue/50 p-3 text-xs">
              <p className="text-slate-300">Your password (copy this):</p>
              <p className="font-mono text-warroom-amber">{generatedPassword}</p>
            </div>
          )}
        </div>

        <div>
          <h2 className="font-pixel text-warroom-cyan">Login</h2>
          <p className="text-xs text-slate-400">Use your generated password to sign in.</p>
          <form className="mt-3 space-y-3" onSubmit={handleLogin}>
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Email" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} required />
            <input className="w-full rounded border border-slate-700 bg-warroom-blue/60 px-3 py-2 text-sm" placeholder="Password" type="password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} required />
            <button className="w-full rounded border border-slate-600 bg-warroom-amber/30 py-2 text-xs font-bold tracking-wide text-warroom-amber" type="submit">Login</button>
          </form>
          {message && <p className="mt-3 text-xs text-slate-300">{message}</p>}
        </div>
      </div>
    </div>
  )
}
