import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { App } from '../components/App'
import { I18nProvider } from '../i18n/I18n'
import { CollectionNotice } from './CollectionNotice'

vi.mock('./privacyInfo', () => ({
  usePrivacyInfo: () => ({ status: 'ready', info: {
    policy_version: '2026-09-18', retention_days: 7, room_idle_ttl_minutes: 120,
    maintenance_interval_seconds: 300, raw_profiles_persisted: false,
  }, retry: vi.fn() }),
}))
afterEach(() => {
  cleanup()
  history.replaceState(null, '', '/')
  localStorage.clear()
  sessionStorage.clear()
})

for (const language of ['en', 'he'] as const) {
  for (const path of ['privacy', 'terms', 'accessibility']) {
    test(`${language} ${path}: owner-approved contact is an initial public route, not a private inbox`, () => {
      history.replaceState(null, '', `/${path}?lang=${language}`)
      render(<App />)
      const contact = document.querySelector('.contact-details')!
      expect(contact).toHaveTextContent('yairrrr')
      const link = screen.getByRole('link', { name: language === 'en' ? /MiZeMi GitHub Issues/ : /הפניות של MiZeMi/ })
      expect(link).toHaveAttribute('href', 'https://github.com/yairrrr/MiZeMi/issues')
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
      expect(contact).toHaveTextContent(language === 'en' ? 'Do not include the request details.' : 'אל תכללו את פרטי הבקשה.')
      expect(contact).toHaveTextContent(language === 'en' ? 'This page does not provide a private channel.' : 'עמוד זה אינו מספק ערוץ פרטי.')
      expect(contact).toHaveTextContent(language === 'en' ? 'access to the repository' : 'הרשאת גישה למאגר')
      expect(document.querySelector('a[href^="mailto:"], a[href^="tel:"]')).toBeNull()
      expect(contact.textContent).not.toMatch(/has not yet been published|טרם פורסם|@[a-z0-9.-]+\.[a-z]{2,}/i)
      expect(document.querySelector('time')).toHaveAttribute('datetime', '2026-09-19')
    })
  }
  test(`${language}: collection notice identifies the operator and warns against personal data in Issues`, () => {
    history.replaceState(null, '', `/?lang=${language}`)
    render(<I18nProvider><CollectionNotice info={null} /></I18nProvider>)
    expect(screen.getByText('yairrrr')).toBeVisible()
    expect(document.querySelector('.contact-details')).toHaveTextContent(language === 'en'
      ? 'Personal details and identity verification require a separately agreed private channel'
      : 'מסירת פרטים אישיים ואימות זהות דורשים ערוץ פרטי שתואם בנפרד')
    expect(screen.getByRole('link', { name: /MiZeMi/ })).toHaveAttribute('href', 'https://github.com/yairrrr/MiZeMi/issues')
  })
}
