Status: Locked (2026-11-18)

# 02 Design: AI Bookkeeper (web)

Decisions: `planning/decisions.md` (D-012, D-017).

Source: `planning/00-brief.md`, `planning/01-prd.md`. Scope: the boss-only web app. Telegram UI is plain bot text and buttons, not covered here.

Platform: Vite + React SPA (client-side routing). This supersedes "Next.js" in the brief constraints. Tailwind + shadcn/ui, Phosphor icons, Montserrat.

## 1. Brand personality

Calm. Exact. Plain. Quiet. Trustworthy.

The web app is a verification tool. It should feel like a printed ledger: black ink on white paper, dense rows, nothing decorative.

| Do | Don't |
| --- | --- |
| Black and white UI; colour only inside charts | Gradients, glows, glassmorphism, neon, coloured accents |
| Tables first; numbers right-aligned, tabular | Hero sections, marketing copy, feature cards |
| Plain text wordmark (business name) | Logos, mascots, illustrations, emoji |
| Hairline 1px borders to separate | Heavy drop shadows, floating cards |
| Small radius (4px) | Oversized rounded cards, pill-everything |
| Headings are plain sentence-case text | Eyebrows (small uppercase kicker labels above headings) |
| Icons only where they add meaning, one weight | Decorative icon-in-circle tiles |
| Short, literal labels ("Trial balance", "Save") | Exclamation marks, cheerful filler, "AI-powered" |
| Status shown by text + outline/filled badge | Status shown by colour alone |
| Motion only for state change (sheet open, toast) | Animated counters, parallax, skeleton shimmer |

## 2. Colour tokens

Defined as CSS variables on `:root` (light) and `.dark` (dark), mapped into the shadcn/ui token names. Hex shown; implement as hex or the equivalent HSL/OKLCH.

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--background` | `#FFFFFF` | `#0A0A0A` | Page |
| `--foreground` | `#0A0A0A` | `#F5F5F5` | Body text, figures |
| `--card` | `#FFFFFF` | `#0A0A0A` | Same as page (no raised surfaces) |
| `--card-foreground` | `#0A0A0A` | `#F5F5F5` | |
| `--popover` | `#FFFFFF` | `#111111` | Menus, popovers, sheet, dialog |
| `--popover-foreground` | `#0A0A0A` | `#F5F5F5` | |
| `--primary` | `#0A0A0A` | `#F5F5F5` | Primary button fill, active tab underline |
| `--primary-foreground` | `#FFFFFF` | `#0A0A0A` | Text on primary |
| `--secondary` | `#F4F4F4` | `#171717` | Secondary button fill |
| `--secondary-foreground` | `#0A0A0A` | `#F5F5F5` | |
| `--muted` | `#F4F4F4` | `#171717` | Table header row, subtotal rows, code chips |
| `--muted-foreground` | `#525252` | `#A3A3A3` | Secondary text, captions, column headers |
| `--accent` | `#EDEDED` | `#1F1F1F` | Hover row, hover menu item, ghost button hover |
| `--accent-foreground` | `#0A0A0A` | `#F5F5F5` | |
| `--accent-selected` | `#E3E3E3` | `#2A2A2A` | Selected row (entry open in sheet), pressed state |
| `--border` | `#E0E0E0` | `#2A2A2A` | Hairlines between rows, section dividers |
| `--border-strong` | `#0A0A0A` | `#F5F5F5` | Statement total rules (single above, double below) |
| `--input` | `#8A8A8A` | `#737373` | Input, select, checkbox outlines (>= 3:1 vs bg) |
| `--ring` | `#0A0A0A` | `#F5F5F5` | Focus ring |
| `--destructive` | `#B42318` | `#F97066` | TB imbalance warning, delete/revoke confirm, form errors. Sparingly. |
| `--destructive-foreground` | `#FFFFFF` | `#0A0A0A` | |
| `--chart-1` | `#1D6FA3` | `#5AA9E6` | Series 1 (blue) |
| `--chart-2` | `#C2570C` | `#F28C3C` | Series 2 (orange) |
| `--chart-3` | `#2F7D4F` | `#5CC08A` | Series 3 (green) |
| `--chart-4` | `#A23B72` | `#E07BB0` | Series 4 (magenta) |
| `--chart-5` | `#8C6D1F` | `#D4B24C` | Series 5 (ochre) |
| `--chart-positive` | `#2F7D4F` | `#5CC08A` | Net profit >= 0 bars |
| `--chart-negative` | `#B42318` | `#F97066` | Net profit < 0 bars |
| `--chart-grid` | `#E0E0E0` | `#2A2A2A` | Gridlines |
| `--chart-axis` | `#525252` | `#A3A3A3` | Axis labels, ticks |

Contrast (checked): fg on bg 19.8:1 light / 18.2:1 dark. Muted-fg on bg 7.8:1 / 7.9:1; on muted 7.1:1 / 7.1:1. Input outline 3.45:1 / 4.2:1. Destructive 6.6:1 / 7.1:1. Every chart colour >= 4.5:1 on its background (light lowest 4.5:1 for chart-2; dark lowest 7.1:1).

Rules
- No colour in UI chrome. Buttons, tabs, badges, links: black/white/grey only.
- Links: `--foreground`, underlined. Hover: thicker underline (2px).
- Positive/negative in tables never use colour; negatives use parentheses (section 9).
- Chart colours are assigned in fixed order; a series keeps its colour across all charts (e.g. Revenue always chart-1).

## 3. Theme

| Item | Rule |
| --- | --- |
| Default | Follows system (`prefers-color-scheme`) |
| Toggle | Header icon button cycles System / Light / Dark. Icon: `Desktop` / `Sun` / `Moon`. Tooltip + `aria-label` state the current mode |
| Persistence | `localStorage` key `theme`; class `dark` on `<html>` set before first paint (inline script in `index.html`) to avoid flash |
| Dark mode | Pure inverse: near-black bg, near-white text, same structure. No extra surfaces or tints |

## 4. Typography

Font: Montserrat via Google Fonts only. Load weights 400, 500, 600 (no italics). `display=swap`. Fallback stack: `Montserrat, ui-sans-serif, system-ui, sans-serif`.

```
https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600&display=swap
```

| Token | Size / line height | Weight | Use |
| --- | --- | --- | --- |
| `text-xs` | 12px / 16px | 500 | Badges, chart axis labels, table footnotes |
| `text-sm` | 13px / 20px | 400 | Table cells (default density), inputs, buttons, helper text |
| `text-base` | 14px / 22px | 400 | Body text, form labels (500), sheet content |
| `text-lg` | 16px / 24px | 600 | Section headings inside a page, sheet title |
| `text-xl` | 20px / 28px | 600 | Page title (one per page) |
| `text-2xl` | 24px / 32px | 600 | Headline figures on Analytics only |

Rules
- Money and all numeric columns: `font-variant-numeric: tabular-nums` (`tabular-nums` utility). Applied on `<td>`, totals, chart labels, inputs for amounts.
- Amount columns right-aligned; header of an amount column also right-aligned.
- Entry numbers, account codes: tabular-nums, left-aligned.
- Sentence case everywhere. No all-caps text, no letter-spaced labels, no eyebrows.
- Weight 600 is the maximum. Totals rows use 600; everything else 400 or 500.
- Max text line length 72ch for prose (help text, empty states).

## 5. Spacing, radius, borders

Spacing scale (4px base, Tailwind steps): `1`=4, `2`=8, `3`=12, `4`=16, `6`=24, `8`=32, `12`=48.

| Context | Value |
| --- | --- |
| Table cell padding (default) | 6px vertical, 12px horizontal (row height 32px) |
| Table cell padding (compact, Journal) | 4px vertical, 8px horizontal (row height 28px) |
| Form field gap | 16px between fields, 6px label to input |
| Section gap inside page | 24px |
| Page padding | 16px (< 768px), 24px (>= 768px) |
| Header height | 48px |

Radius
| Token | Value | Use |
| --- | --- | --- |
| `--radius` | 4px | Buttons, inputs, selects, badges, dialogs, sheet edges, popovers |
| `rounded-none` | 0 | Tables, table containers, chart frames |

Borders vs shadows
- Separation is done with 1px `--border` lines. No shadows on cards, tables, tabs or buttons.
- Only floating layers get a shadow, and only one: popover, dropdown menu, dialog, sheet, toast use `0 1px 2px rgb(0 0 0 / 0.08)` plus a 1px border. In dark mode, the border does the work; shadow is the same token.
- No nested bordered boxes. A table inside a section is not wrapped in an extra card.

## 6. Layout

### App shell
```
+-------------------------------------------------------------------------+
| Business Name   Accounting  Analytics  Settings     [Open in Telegram] [theme] [account] |
+-------------------------------------------------------------------------+
| Page title                                      [date range filter]      |
| Tabs (Accounting only)                                                   |
| Content (table / chart / form)                                           |
+-------------------------------------------------------------------------+
```

| Element | Rule |
| --- | --- |
| Top bar | 48px, bottom border, sticky. Left: business name wordmark (text-base 600, links to `/accounting/journal`). Nav: Accounting / Analytics / Settings as text links; active = 2px `--primary` underline + 600. Right: "Open in Telegram" secondary button (icon `TelegramLogo` + label), theme toggle, account menu (email, Sign out) |
| No sidebar | Top nav only. Settings uses a left section list inside the page |
| Max widths | Accounting and Analytics: 1280px centred. Settings: 960px (section list 200px + form max 560px). Sign-in, access denied, setup: 440px |
| Page header | Title (text-xl) left; date range filter right on the same row (wraps below at < 768px) |
| Table density | Default 32px rows; Journal 28px rows (compact). Zebra striping off; hairline row borders |
| Sticky table header | `position: sticky; top: 48px` (below top bar) with `--muted` bg and bottom border. In scroll container, `top: 0` |
| Sticky first column | Account/description column sticky left when the table scrolls horizontally |
| Totals row | Sticky bottom in long tables (Journal, GL); 600 weight; top border `--border-strong` |

### Responsive
| Breakpoint | Behaviour |
| --- | --- |
| >= 1024px | Full layout as above |
| 768 to 1023px | Settings section list becomes a select at top of page. Date filter wraps under title |
| < 768px (down to 375px) | Nav collapses to a `List` icon button opening a sheet from the left with the three links, Open in Telegram, theme, sign out. Wordmark truncates with ellipsis. Accounting tabs become a horizontally scrollable tab list (no wrap). Entry detail sheet is full-width |
| Tables at any width | Table sits in its own container with `overflow-x: auto`. Only that container scrolls horizontally; the page body never does (`overflow-x: clip` on body). Min table width set per table so columns never squash below legibility |
| Charts | Full container width, fixed height 280px (240px < 768px); legend wraps above chart |

## 7. Routes (SPA)

All routes except `/sign-in` and `/access-denied` require a session (F-001.2). If settings are missing, every route redirects to `/setup` (F-002.1). Date range lives in query params so views are linkable: `?range=this-month` or `?range=custom&from=2026-10-01&to=2026-10-31`.

## 8. Screen inventory

| Screen | Route | PRD |
| --- | --- | --- |
| Sign in | `/sign-in` | F-001.1 |
| Access denied | `/access-denied` | F-001.1 |
| First-run setup | `/setup` | F-002.1, F-002.2, F-002.3 |
| Accounting: Journal | `/accounting/journal` | F-024.1, F-024.2, F-024.4 |
| Entry detail sheet | `/accounting/journal/:entryNo` (sheet over Journal) | F-024.3, G-2, G-7 |
| Accounting: General ledger | `/accounting/ledger?account=:code` | F-025.1, F-025.2 |
| Accounting: Trial balance | `/accounting/trial-balance` | F-026.1, F-026.3 |
| Accounting: Adjusted trial balance | `/accounting/adjusted-trial-balance` | F-026.2, F-026.3 |
| Accounting: P&L | `/accounting/pnl` | F-027.1 |
| Accounting: Balance sheet | `/accounting/balance-sheet` | F-027.2 |
| Accounting: Cash flow | `/accounting/cash-flow` | F-027.3 |
| Analytics | `/analytics` | F-028.1 to F-028.4 |
| Settings: Business | `/settings/business` | F-002.2, F-002.3, F-002.4 |
| Settings: Chart of accounts | `/settings/accounts` | F-003.1, F-003.2 |
| Settings: Opening balances | `/settings/opening-balances` | F-004.1 to F-004.3 |
| Settings: Fixed assets | `/settings/assets` | F-021.1 to F-021.3 |
| Settings: Suppliers | `/settings/suppliers` | F-003.3, F-007.1, F-007.2, F-007.4 |
| Settings: Users and roles | `/settings/users` | F-008.1, F-008.2 |
| Settings: Telegram connection | `/settings/telegram` | F-006.1, F-006.2, F-006.4 |
| Header: Open in Telegram | all signed-in routes | F-029.1 |
| Not found | `*` | n/a |

Default landing after sign-in: `/accounting/journal?range=this-month`.

## 9. Number and date formatting

| Item | Rule | Example |
| --- | --- | --- |
| Currency | Business currency from settings (SGD). Symbol not repeated in every cell; column header says "Amount (SGD)". Headline figures and chart tooltips prefix `S$` | `S$12,450.00` |
| Decimals | Always 2 dp in tables and statements. Charts axes may drop to 0 dp ("12k") but tooltips show 2 dp | `1,850.00` |
| Thousands | Comma separator | `12,450.00` |
| Negatives in statements, TB, GL running balance | Parentheses, no minus sign, no colour | `(1,204.50)` |
| Negatives in inputs | Minus sign accepted on input, shown formatted on blur | `-50` becomes `(50.00)` |
| Zero | `0.00` in statements; blank cell in debit/credit columns where the line has no value | |
| Debit/credit columns | Two separate columns, never signed amounts | |
| Percent | 1 dp with `%` | `62.4%` |
| Date (display) | `D MMM YYYY`, no leading zero, business timezone (G-6) | `18 Nov 2026` |
| Date range | `1 Oct 2026 to 31 Oct 2026`; same month: `1 to 31 Oct 2026` | |
| Month label (charts) | `MMM YY` | `Nov 26` |
| Timestamp (audit trail) | `18 Nov 2026, 21:04` (24h, business TZ) | |
| Date (input/URL) | ISO `YYYY-MM-DD` | `2026-11-18` |
| Entry number | `JE-` + zero-padded | `JE-00042` |

Implementation: one shared `formatMoney`, `formatDate`, `formatPercent` module using `Intl.NumberFormat('en-SG')` and `Intl.DateTimeFormat('en-SG', { timeZone })`. Money arrives from the API as decimal strings; never parse to float for display maths.

## 10. Icons

Phosphor (`@phosphor-icons/react`), weight `regular` only. Sizes: 16px inline with text and in buttons, 20px for icon-only buttons in the header. Colour inherits `currentColor`. Icon-only buttons always have `aria-label` and a tooltip.

| Use | Icon |
| --- | --- |
| Open in Telegram | `TelegramLogo` |
| Theme | `Desktop`, `Sun`, `Moon` |
| Account menu | `UserCircle` |
| Mobile nav | `List` |
| Date filter | `CalendarBlank` |
| Check pass / fail | `Check` / `X` |
| Warning (TB imbalance) | `Warning` |
| Document preview | `FileText`, `Image` |
| Open external / new tab | `ArrowSquareOut` |
| Copy link | `Copy` |
| Close sheet/dialog | `X` |
| Reversal link | `ArrowsCounterClockwise` |
| Sort | `CaretUp`, `CaretDown` |

## 11. Components and states

shadcn/ui primitives, restyled with the tokens above. Shared state rules first, then per-component specifics.

### Shared states
| State | Rule |
| --- | --- |
| Default | Tokens as defined; no shadow |
| Hover | Bg `--accent` (rows, ghost/secondary buttons, menu items). Primary button: 90% opacity |
| Focus | `:focus-visible` only: 2px `--ring` outline, 2px offset. Never removed |
| Disabled | 50% opacity, `cursor: not-allowed`, `aria-disabled`. Reason given in a tooltip or helper text where not obvious |
| Loading | Buttons: label kept, 16px spinner (`CircleNotch`, rotating) replaces icon, button disabled. Tables: header rendered, body shows 5 rows of static `--muted` bars (no shimmer). Charts: empty frame with "Loading" text |
| Empty | Plain text in the table body or chart frame: what is missing + one action link where one exists. No illustrations |
| Error | Inline text in `--destructive` with `Warning` icon, plus "Retry" text button. Form fields: red text below field, `aria-invalid`, `aria-describedby` |

### Global components
| Component | Spec | States |
| --- | --- | --- |
| Button: primary | `--primary` fill, `--primary-foreground` text, 32px high, 4px radius, text-sm 500 | all shared |
| Button: secondary | 1px `--input` border, transparent bg | all shared |
| Button: ghost | No border; hover `--accent` | all shared |
| Button: destructive | Outline in `--destructive` text + border; only inside confirm dialogs | all shared |
| Input / Select / Textarea | 32px, 1px `--input` border, 4px radius, text-sm. Amount inputs right-aligned, tabular-nums | default, hover (border `--foreground`), focus, disabled, error |
| Checkbox / Switch | shadcn defaults in monochrome; checked = `--primary` fill | default, focus, disabled |
| Tabs | Text tabs, underline style. Active: 600 weight + 2px `--primary` bottom border. Inactive: `--muted-foreground` | hover (fg colour), focus, disabled |
| Table | See section 6. Header text-xs 500 `--muted-foreground` on `--muted`. Clickable rows: `cursor: pointer`, hover `--accent`, selected `--accent-selected` | loading, empty, error |
| Badge | text-xs 500, 20px high, 4px radius. Two variants only: outline (1px `--foreground` border, transparent) and filled (`--foreground` bg, `--background` text). Muted variant (`--muted` bg, `--muted-foreground` text) for inactive things | static |
| Tooltip | `--foreground` bg, `--background` text, text-xs, no arrow | |
| Sheet | Right side, 560px wide (full width < 768px), 1px left border, shadow token. Header with title + close `X`. Body scrolls; header sticky | open, loading, error |
| Dialog | 440px max, centred, 1px border, shadow token. Title, 1 to 2 lines body, actions right-aligned (Cancel secondary, action primary or destructive) | open, submitting, error |
| Toast (Sonner) | Bottom-right (bottom-centre < 768px), 1px border, shadow token, text-sm, auto-dismiss 4s, pauses on hover. Success: `Check` icon. Error: `Warning` icon + destructive text, stays until dismissed. Max 3 visible | |
| Date range filter | See below | |
| Account menu | Dropdown: email (muted), Sign out | |

### Badges: entry source and status (monochrome)
| Badge | Variant | Text |
| --- | --- | --- |
| Source: auto | outline | Auto |
| Source: boss approved | outline | Approved |
| Source: manual | outline | Manual |
| Source: adjusting | outline | Adjusting |
| Source: opening | outline | Opening |
| Source: reversal | outline | Reversal |
| Status: posted | filled | Posted |
| Status: pending approval | outline, dashed border | Pending |
| Status: rejected | muted | Rejected |
| Status: proposed | muted | Proposed |
| Entry reversed (has a reversal) | muted, with `ArrowsCounterClockwise` | Reversed |
| Period: open / closing / locked | outline / outline dashed / filled | Open / Closing / Locked |
| Check: pass / fail | text + `Check` / filled + `X` | Pass / Fail |
| User: active / deactivated / blocked | filled / muted / muted | Active / Deactivated / Blocked |
| Role: boss / supplier | filled / outline | Boss / Supplier |
| Supplier: active / inactive | filled / muted | Active / Inactive |
| Account type | outline | Asset, Liability, Equity, Revenue, Expense, Contra-asset |

Badges are never the only signal: the column header or adjacent text names the attribute.

### Date range filter (F-024.2, F-025.2, F-028.4)
| Item | Spec |
| --- | --- |
| Trigger | Secondary button: `CalendarBlank` + current label ("This month: 1 to 30 Nov 2026") |
| Popover | Left: preset list (This month, Last month, Last 3 months, Year to date, Last 12 months, Custom). Right (Custom only): two-month calendar range picker + From/To date inputs. Apply / Cancel |
| Year to date | Uses financial year start month from settings |
| As-at tabs | TB, ATB, Balance sheet use the range end date; label reads "As at 30 Nov 2026" |
| State | Stored in URL query; persists across Accounting tabs and Analytics |
| Errors | From after To: inline error, Apply disabled. Future To date clamps to today |
| Keyboard | Presets are a radio group (arrow keys); calendar uses shadcn keyboard support; Esc closes |

## 12. Screens

### Sign in (F-001.1)
- Centred 440px column: business name if known else "AI Bookkeeper" (text-xl), one line "Sign in to view the books.", primary button "Continue with Google".
- States: loading (button spinner while redirecting), error (inline "Sign-in failed. Try again.").

### Access denied (F-001.1)
- Same column. Title "Access denied". Text: "This Google account is not allowed. Sign in with the owner's account." Button "Use another account" (signs out, back to `/sign-in`). No business data, no business name.

### First-run setup (F-002.1 to F-002.3)
- Single page form, 560px, fields grouped under plain headings: Business (name, currency, timezone, FY start month), GST (registered switch, rate), Rules (price-change rule, duplicate window days, reminder lead days), Schedule (daily recap time, monthly report day and time). Defaults pre-filled from PRD.
- Primary "Save and continue". On success go to `/settings/telegram` with toast "Settings saved".
- Errors inline per field (GST rate 0 to 100, valid HH:MM); nothing saves until all valid. Nav links disabled until saved.

### Accounting page
Shared: page title "Accounting", date range filter, tab list (Journal, General ledger, Trial balance, Adjusted trial balance, P&L, Balance sheet, Cash flow). Each tab is its own route. Read-only (G-8): no edit controls anywhere.

| Tab | Columns / structure | Specifics |
| --- | --- | --- |
| Journal | Date, Entry no., Description, Account, Debit, Credit, Source, Status | Compact density. One row per line; entry-level cells (date, no., description, badges) shown on the first line only, entry groups separated by a `--border-strong` 1px rule at 20% opacity. Row click opens entry sheet. Footer: Total debit, Total credit (must be equal; if not, destructive warning row). Filter-by-source select and text search (description, entry no.) above table. Empty: "No entries in this range." |
| General ledger | Account picker (combobox: code + name, searchable). Table: Date, Entry no., Description, Debit, Credit, Balance | First row "Opening balance", last row "Closing balance" (600). Running balance with parentheses for credit-side balances on debit-normal accounts. Empty account picker state: "Pick an account to see its postings." |
| Trial balance | Code, Account, Debit, Credit | Non-zero accounts only. Totals row. Period status badge next to title |
| Adjusted trial balance | Code, Account, Unadjusted Dr, Unadjusted Cr, Adjustments Dr, Adjustments Cr, Adjusted Dr, Adjusted Cr | For closed months shows both sets (F-026.2). For open periods, note: "Adjustments post at month-end close." |
| P&L | Statement layout: Revenue, COGS, Gross profit, Operating expenses, Operating profit, Other items, Net profit. Columns: Line, Amount; optional Prior period column | Section headings 600; subtotals with single top rule; Net profit with single top and double bottom rule (`border-bottom: 3px double`). Accounts indented 16px under sections |
| Balance sheet | Assets, Liabilities, Equity with subtotals | Check line at bottom: "Assets = Liabilities + Equity" with `Check` + "Balanced" or destructive `Warning` + difference |
| Cash flow | Operating (net profit, depreciation add-back, change in payables, other working capital), Investing, Financing, Net change, Opening cash + bank, Closing cash + bank | Check line: "Net change equals change in cash and bank" pass/fail as above |

TB imbalance warning (F-026.3, F-024.4): full-width row above table, 1px `--destructive` border, `Warning` icon, text "Totals do not match. Difference: S$12.50." `role="alert"`. This is the one place destructive colour appears on a normal page.

### Entry detail sheet (F-024.3)
Opens from Journal row; URL updates to `/accounting/journal/JE-00042` (back closes it). Sections in order, separated by 1px rules, each with a text-lg heading:

| Section | Content |
| --- | --- |
| Header | `JE-00042` + date + description; source and status badges; period badge |
| Lines | Table: Account (code + name), Memo, Debit, Credit; totals row |
| Checks | List of F-013 checks: name, Pass/Fail badge, detail text (e.g. "Unit price 12.40, last 11.80"). Failed checks first. Absent for manual/opening entries: "No automated checks for manual entries." |
| Document | Invoice metadata (supplier, invoice no., invoice date, due date, total). Preview: PDF in an inline `<iframe>` (height 480px), image as `<img>` fit to width. Link "Open in new tab" (`ArrowSquareOut`). Error: "Document could not be loaded." Not present: section hidden |
| Reversal | If reversed: "Reversed by JE-00057" link. If this is a reversal: "Reverses JE-00042" link. Links swap the sheet content |
| Audit trail | Chronological list: timestamp, actor (Agent, Boss, System), action, model where present. text-sm, muted timestamps |

States: loading (section skeleton bars), error ("Could not load entry JE-00042." + Retry), not found ("Entry not found.").

### Analytics (F-028)
Page title "Analytics", date range filter. Layout: one column of charts, each a section with heading, chart, and "Show as table" toggle.

| Chart | Type | Series / colour |
| --- | --- | --- |
| Revenue, expenses, net profit by month | Grouped bars, last 12 months (or filter) | Revenue chart-1, Expenses chart-2, Net profit positive/negative |
| Profit margins by month | Lines with point markers | Gross chart-1, Operating chart-3, Net chart-4 |
| Spend by supplier by month | Stacked bars | Top 4 suppliers chart-1..4, "Other" chart-5 |
| Top 5 cost accounts | Horizontal bars, sorted descending, single colour chart-2 | Value labels at bar end |

Above the charts: a row of 4 headline figures (Revenue, Gross margin %, Net profit, Payables) as plain text: muted label on one line, text-2xl figure below. No boxes, no icons, no trend arrows.

Chart rules
- Library: Recharts via shadcn/ui chart wrapper, coloured with `--chart-*` tokens.
- No 3D, no shadows, no gradients, no rounded bar tops beyond 2px, no animation (or disabled under reduced motion).
- Gridlines: horizontal only, 1px `--chart-grid`. No vertical gridlines. Axis lines off except baseline.
- Zero baseline always visible; bars start at zero. Margin % axis shows `%`.
- Direct labels where possible: line series labelled at right end; single-series bars labelled at bar end. Legend only for grouped/stacked bars, placed top-left, text not swatches alone.
- Tooltip: date + each series value in 2 dp, tabular-nums; matches table values exactly.
- Max 5 categorical colours; more categories roll into "Other".
- Empty: "Not enough data for this range." inside the chart frame.

### Settings
Left section list (Business, Chart of accounts, Opening balances, Fixed assets, Suppliers, Users and roles, Telegram). Each section is its own route and saves independently.

| Section | Layout | Actions and states |
| --- | --- | --- |
| Business (F-002) | Same form as setup | Save (primary). Note under form: "Changes apply to new events only." Inline errors; success toast |
| Chart of accounts (F-003) | Table: Code, Name, Type badge, Status, Postings count | "Add account" opens dialog (code, name, type). Row menu: Deactivate (only for accounts with no postings; otherwise disabled with tooltip "Has postings"). No delete or type change for accounts with postings. Duplicate code: inline error. Inactive accounts shown with muted badge, filter "Show inactive" |
| Opening balances (F-004) | "As at" date input, then table: Code, Account, Debit input, Credit input. Sticky footer: Total debit, Total credit, Difference | Difference shown live; non-zero difference in destructive text and Save disabled with helper "Debits must equal credits." Saving when an opening entry exists opens confirm dialog: "This reverses JE-00001 and posts a new opening entry." |
| Fixed assets (F-021) | Table: Name, Purchase date, Cost, Salvage, Life (months), Accumulated depreciation, Net book value | "Add asset" dialog (name, purchase date, cost, salvage, life, method fixed to Straight-line, asset account). Validation: salvage < cost, life >= 1 |
| Suppliers (F-007) | Table: Name, UEN, Default account, Terms (days), Telegram, Status | "Add supplier" dialog. Row actions: Edit, Create invite, Deactivate (confirm dialog). Create invite opens dialog showing link in read-only input + "Copy link" button, expiry "Expires 25 Nov 2026, 21:04", single-use note. Copy success toast "Link copied" |
| Users and roles (F-008) | Table: Display name, @username, Role badge, Linked supplier, Status, Linked date | Row menu (suppliers only): Change linked supplier (dialog with select), Deactivate, Revoke link (destructive confirm). Boss row has no destructive actions; note "There is exactly one boss." Empty: "No one has linked Telegram yet." |
| Telegram (F-006) | Status line: "Not connected" or "Connected as @username" (filled badge) | "Connect Telegram" (primary) or "Reconnect" (secondary) generates token; shows link in read-only input + Copy, "Open in Telegram" link, and QR code (200px, black on white in both themes, with 16px white quiet zone), expiry text. Reconnect warns in dialog: "Your current Telegram account will be disconnected." Poll every 5s while a token is shown; on bind, replace with connected state + toast |

Open in Telegram header button (F-029): secondary button linking to `https://t.me/<bot username>`, `target="_blank" rel="noopener"`. Below 768px it moves into the nav sheet.

## 13. Accessibility

| Area | Rule |
| --- | --- |
| Contrast | WCAG AA: text >= 4.5:1, large text and UI boundaries >= 3:1. Verified for tokens in section 2. Do not place muted-fg on accent-selected below 4.5:1 |
| Focus | Visible 2px `--ring` outline on every interactive element via `:focus-visible`. Never `outline: none` without replacement |
| Skip link | "Skip to content" first focusable element, visible on focus |
| Keyboard: tabs | shadcn/Radix Tabs: arrow keys move between tabs, Home/End jump, Enter/Space activates; tabs are links to routes |
| Keyboard: tables | Clickable rows are focusable (`tabindex="0"`, row role link or a link in the entry-no. cell); Enter opens the sheet; Up/Down move row focus in Journal. Sortable headers are buttons with `aria-sort` |
| Keyboard: overlays | Sheet and dialog trap focus, Esc closes, focus returns to the triggering row/button |
| Semantics | Real `<table>` with `<th scope>`; statements use table markup with row headers. Amount cells have no visual-only meaning (parentheses read as "negative" via `aria-label` on negative cells, e.g. "negative 1,204.50") |
| Status | Never colour alone: pass/fail uses text + icon + badge variant. Warnings use `role="alert"` |
| Charts | Each chart has `role="img"` with an `aria-label` summarising it ("Net profit by month, Dec 25 to Nov 26, highest S$4,210.00 in Oct 26") and a "Show as table" toggle rendering the same data as an accessible table. Series distinguished by direct labels or legend text, not colour only; line series also differ by marker shape |
| Motion | Minimal by default: sheet/dialog 150ms fade+slide, toast 150ms fade. Under `prefers-reduced-motion: reduce`, all transitions and chart animation off |
| Zoom | Layout works at 200% zoom and 375px width without page horizontal scroll (tables scroll in their container) |
| Language | `<html lang="en-SG">` |
| Forms | Every input has a visible `<label>`; required fields marked "(required)" in text, not asterisk only; errors announced via `aria-live="polite"` |
| Session | After sign out, book data is not shown from cache (F-001.3): API responses `Cache-Control: no-store`; client query cache cleared on sign out |

## 14. Copy rules

- Literal and short: "Save", "Add supplier", "Create invite", "Copy link", "Connect Telegram".
- Errors say what happened and what to do: "Debits must equal credits. Difference: S$12.50."
- Empty states state the fact, then one action if there is one.
- No exclamation marks, no emoji, no "AI", no "magic", no em dashes.
