import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { TooltipProvider } from '@/components/ui/tooltip'
import { setViewportWidth } from '@/test/viewport'
import { ThemeToggle } from './theme-toggle'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('theme toggle (D-017)', () => {
  it('cycles System, Light, Dark and persists the choice', async () => {
    setViewportWidth(1280)
    const user = userEvent.setup()
    render(
      <TooltipProvider>
        <ThemeToggle />
      </TooltipProvider>,
    )

    await user.click(screen.getByRole('button', { name: 'Theme: System' }))
    expect(window.localStorage.getItem('theme')).toBe('light')
    expect(document.documentElement).not.toHaveClass('dark')

    await user.click(screen.getByRole('button', { name: 'Theme: Light' }))
    expect(window.localStorage.getItem('theme')).toBe('dark')
    expect(document.documentElement).toHaveClass('dark')

    await user.click(screen.getByRole('button', { name: 'Theme: Dark' }))
    expect(window.localStorage.getItem('theme')).toBeNull()
    expect(document.documentElement).not.toHaveClass('dark')
    expect(screen.getByRole('button', { name: 'Theme: System' })).toBeInTheDocument()
  })
})
