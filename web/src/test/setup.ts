import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './server'

beforeAll(() => {
  window.scrollTo = () => undefined
  server.listen({ onUnhandledFrame: 'error' })
})
afterEach(() => {
  cleanup()
  server.resetHandlers()
  window.localStorage.clear()
  document.documentElement.classList.remove('dark')
})
afterAll(() => server.close())
