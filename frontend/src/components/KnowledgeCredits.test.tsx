import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, expect, test, vi } from 'vitest'
import { KnowledgeCredits } from './KnowledgeCredits'
import { I18nProvider, LANGUAGE_STORAGE_KEY } from '../i18n/I18n'

afterEach(() => { cleanup(); localStorage.clear(); vi.unstubAllGlobals() })
test.each(['en', 'he'])('reference attribution is accessible and makes no requests: %s', async (language) => {
  localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  render(<I18nProvider><KnowledgeCredits /></I18nProvider>)
  await userEvent.setup().click(screen.getByText(language === 'he' ? 'איך נוצרים החיבורים' : 'How the connections work'))
  const link = screen.getByRole('link', { name: 'GeoNames' })
  expect(link).toBeVisible()
  expect(link).toHaveAttribute('href', 'https://www.geonames.org/')
  expect(link).toHaveAttribute('rel', 'noreferrer')
  expect(screen.getByRole('link', { name: 'CC BY 4.0' })).toBeVisible()
  expect(fetch).not.toHaveBeenCalled()
})
