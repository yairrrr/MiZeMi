import { useI18n } from '../i18n/I18n'

export function LegalFooter({ inGame = false }: { inGame?: boolean }) {
  const { t, language } = useI18n()
  return <footer className="legal-footer">
    <nav aria-label={t('Privacy and accessibility')}>
      {(['privacy', 'terms', 'accessibility'] as const).map(page => <a key={page}
        href={`/${page}?lang=${language}`} target={inGame ? '_blank' : undefined}
        rel={inGame ? 'noopener noreferrer' : undefined}>
        {t(page === 'privacy' ? 'Privacy' : page === 'terms' ? 'Terms' : 'Accessibility')}
        {inGame && <span className="sr-only">{t(' (opens in a new tab)')}</span>}
      </a>)}
    </nav>
    {inGame && <small>{t('These links open a new tab so you can keep your place in the game.')}</small>}
  </footer>
}
