import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, expect, vi } from 'vitest'
import { server } from './server'

beforeAll(() => {
  window.scrollTo = () => undefined
  window.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  server.listen({ onUnhandledFrame: 'error' })
})
const inFlight = new Set<string>()
server.events.on('request:start', ({ requestId }) => inFlight.add(requestId))
server.events.on('request:end', ({ requestId }) => inFlight.delete(requestId))

afterEach(async () => {
  cleanup()
  await vi.waitFor(() => expect(inFlight.size).toBe(0))
  server.resetHandlers()
  window.localStorage.clear()
  document.documentElement.classList.remove('dark')
})
afterAll(() => server.close())
