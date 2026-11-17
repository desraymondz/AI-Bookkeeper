import { vi } from 'vitest'

function matches(query: string, width: number): boolean {
  const min = /min-width:\s*(\d+)px/.exec(query)
  const max = /max-width:\s*(\d+)px/.exec(query)
  if (min && width < Number(min[1])) return false
  if (max && width > Number(max[1])) return false
  if (query.includes('prefers-color-scheme: dark')) return false
  return Boolean(min || max)
}

export function setViewportWidth(width: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width })
  vi.stubGlobal(
    'matchMedia',
    vi.fn((query: string) => ({
      matches: matches(query, width),
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  )
}
