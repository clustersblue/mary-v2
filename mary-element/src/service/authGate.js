let sessionGate = Promise.resolve()
let guardOwnsRedirect = false
let suppressErrorToasts = false
let suppressTimer = null
let resetSession = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
  sessionStorage.removeItem('token')
  sessionStorage.removeItem('user')
}

export function registerSessionReset(reset) {
  resetSession = reset
}

export function resetSessionNow() {
  try {
    resetSession()
  } catch (e) {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    sessionStorage.removeItem('token')
    sessionStorage.removeItem('user')
  }
}

export function beginSessionValidation(promise) {
  const gated = Promise.resolve(promise).catch(() => {})
  sessionGate = gated
  gated.finally(() => {
    if (sessionGate === gated) sessionGate = Promise.resolve()
  })
}

export function waitForSessionValidation() {
  return sessionGate
}

export function setGuardOwnsRedirect(value) {
  guardOwnsRedirect = Boolean(value)
}

export function guardOwnsRedirectNow() {
  return guardOwnsRedirect
}

export function suppressAuthErrorToasts() {
  suppressErrorToasts = true
  if (suppressTimer) clearTimeout(suppressTimer)
  suppressTimer = setTimeout(() => {
    suppressErrorToasts = false
    suppressTimer = null
  }, 1000)
}

export function authToastsSuppressed() {
  return suppressErrorToasts
}
