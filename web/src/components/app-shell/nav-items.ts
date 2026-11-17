// See planning/02-design.md#6-layout and #8-screen-inventory
export const NAV_ITEMS = [
  { label: 'Accounting', to: '/accounting/journal', section: '/accounting' },
  { label: 'Analytics', to: '/analytics', section: '/analytics' },
  { label: 'Settings', to: '/settings/business', section: '/settings' },
] as const

export type NavItem = (typeof NAV_ITEMS)[number]

export function isSectionActive(pathname: string, section: string) {
  return pathname === section || pathname.startsWith(`${section}/`)
}
