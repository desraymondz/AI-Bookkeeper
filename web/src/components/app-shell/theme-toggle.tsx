import { DesktopIcon, MoonIcon, SunIcon } from '@phosphor-icons/react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { nextThemeMode, type ThemeMode, useThemeMode } from '@/lib/theme'

const THEME_META: Record<ThemeMode, { label: string; Icon: typeof SunIcon }> = {
  system: { label: 'System', Icon: DesktopIcon },
  light: { label: 'Light', Icon: SunIcon },
  dark: { label: 'Dark', Icon: MoonIcon },
}

export function ThemeToggle({ withLabel = false }: { withLabel?: boolean }) {
  const [mode, setMode] = useThemeMode()
  const { label, Icon } = THEME_META[mode]
  const description = `Theme: ${label}`

  if (withLabel) {
    return (
      <Button
        variant="ghost"
        className="justify-start"
        aria-label={description}
        onClick={() => setMode(nextThemeMode(mode))}
      >
        <Icon aria-hidden />
        {description}
      </Button>
    )
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={description}
          onClick={() => setMode(nextThemeMode(mode))}
        >
          <Icon aria-hidden />
        </Button>
      </TooltipTrigger>
      <TooltipContent>{description}</TooltipContent>
    </Tooltip>
  )
}
