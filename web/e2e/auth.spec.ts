import { BUSINESS_NAME, configureBusiness, expect, signIn, test } from './fixtures.ts'

const JOURNAL = '/accounting/journal?range=this-month'

test.describe('T-023 sign-in landing', () => {
  test('a signed-in boss visiting / or /sign-in lands on the journal', async ({ page }) => {
    await signIn(page)
    await configureBusiness(page)
    for (const path of ['/', '/sign-in']) {
      await page.goto(path)
      await expect(page).toHaveURL(new RegExp(`${JOURNAL.replace('?', '\\?')}$`))
    }
  })

  test('Continue with Google starts the Google flow on the API', async ({ page }) => {
    await page.goto('/sign-in')
    await expect(page.getByRole('link', { name: 'Continue with Google' })).toHaveAttribute(
      'href',
      '/api/auth/login',
    )
    await expect(page.getByText('Sign in to view the books.')).toBeVisible()
  })
})

test.describe('T-024 access denied', () => {
  test('shows no business name and requests no business data', async ({ page }) => {
    await signIn(page)
    await configureBusiness(page)
    await page.request.post('/api/auth/logout')
    const configCalls: string[] = []
    page.on('request', (request) => {
      if (request.url().includes('/api/config')) configCalls.push(request.url())
    })
    await page.goto('/access-denied')
    await expect(page.getByRole('heading', { name: 'Access denied' })).toBeVisible()
    await expect(page.getByText(BUSINESS_NAME)).toHaveCount(0)
    expect(configCalls).toEqual([])
  })
})

test.describe('T-027 auth guard', () => {
  for (const path of [
    '/accounting/journal?range=this-month',
    '/analytics?range=this-month',
    '/settings/business',
  ]) {
    test(`redirects ${path} to /sign-in without a session`, async ({ page }) => {
      await page.goto(path)
      await expect(page).toHaveURL(/\/sign-in$/)
      await expect(page.getByRole('link', { name: 'Continue with Google' })).toBeVisible()
    })
  }
})

test.describe('T-028 sign out', () => {
  test('Back after sign out shows no book data and ends on /sign-in', async ({ page }) => {
    await signIn(page)
    await configureBusiness(page)
    await page.goto(JOURNAL)
    await expect(page.getByRole('heading', { name: 'Journal' })).toBeVisible()

    await page.getByRole('button', { name: 'Account' }).click()
    await page.getByRole('menuitem', { name: 'Sign out' }).click()
    await expect(page).toHaveURL(/\/sign-in$/)

    await page.goBack()
    await expect(page).toHaveURL(/\/sign-in$/)
    await expect(page.getByRole('heading', { name: 'Journal' })).toHaveCount(0)
    await expect(page.getByRole('banner')).toHaveCount(0)
  })
})
