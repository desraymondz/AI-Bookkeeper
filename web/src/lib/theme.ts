import { useSyncExternalStore } from 'react'

// See planning/02-design.md#3-theme and planning/decisions.md#D-017
export const THEME_STORAGE_KEY = 'theme'
export const THEME_MODES = ['system', 'light', 'dark'] as const
export type ThemeMode = (typeof THEME_MODES)[number]

const DARK_QUERY = '(prefers-color-scheme: dark)'
const listeners = new Set<() => void>()

function isThemeMode(value: unknown): value is ThemeMode {
  return typeof value === 'string' && (THEME_MODES as readonly string[]).includes(value)
}

export function readThemeMode(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY)
    return isThemeMode(stored) ? stored : 'system'
  } catch {
    return 'system'
  }
}

export function applyThemeMode(mode: ThemeMode) {
  const dark = mode === 'dark' || (mode === 'system' && window.matchMedia(DARK_QUERY).matches)
  document.documentElement.classList.toggle('dark', dark)
}

export function setThemeMode(mode: ThemeMode) {
  try {
    if (mode === 'system') window.localStorage.removeItem(THEME_STORAGE_KEY)
    else window.localStorage.setItem(THEME_STORAGE_KEY, mode)
  } catch {
    return applyThemeMode(mode)
  }
  applyThemeMode(mode)
  for (const listener of listeners) listener()
}

export function nextThemeMode(mode: ThemeMode): ThemeMode {
  return THEME_MODES[(THEME_MODES.indexOf(mode) + 1) % THEME_MODES.length]
}

function subscribe(onChange: () => void) {
  listeners.add(onChange)
  const media = window.matchMedia(DARK_QUERY)
  const onSystemChange = () => {
    if (readThemeMode() === 'system') applyThemeMode('system')
  }
  media.addEventListener('change', onSystemChange)
  return () => {
    listeners.delete(onChange)
    media.removeEventListener('change', onSystemChange)
  }
}

export function useThemeMode(): [ThemeMode, (mode: ThemeMode) => void] {
  const mode = useSyncExternalStore(subscribe, readThemeMode, () => 'system' as ThemeMode)
  return [mode, setThemeMode]
}
