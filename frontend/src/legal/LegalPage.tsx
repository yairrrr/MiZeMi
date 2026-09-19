import { useEffect } from 'react'
import logo from '../assets/mizemi-logo.png'
import { useI18n } from '../i18n/I18n'
import { ContactDetails } from './ContactDetails'
import { legalCopy, type LegalPageName } from './content'
import { RetentionDetails } from './RetentionDetails'
import { usePrivacyInfo } from './privacyInfo'

// Contact-copy update; the backend privacy capability version is unchanged.
const LEGAL_UPDATED_DATE = '2026-09-19'

export function legalPageFromPath(path: string): LegalPageName | null {
  const name = path.replace(/\/$/, '').slice(1)
  return name === 'privacy' || name === 'terms' || name === 'accessibility' ? name : null
}

export function LegalPage({ page }: { page: LegalPageName }) {
  const { t, language } = useI18n()
  const copy = legalCopy[language][page]
  const { info, status, retry } = usePrivacyInfo()
  useEffect(() => {
    document.title = `${copy.title} · MiZeMi`
    return () => { document.title = 'MiZeMi' }
  }, [copy.title])
  return <article className="legal-page">
    <header className="legal-hero">
      <a className="legal-home" href="/" aria-label={t('MiZeMi home')}>
        <img src={logo} alt="MiZeMi" width={1254} height={1254} />
      </a>
      <p className="eyebrow">{t('About your experience')}</p>
      <h1>{copy.title}</h1>
      <p className="legal-date">{t('Updated:')} <time dateTime={LEGAL_UPDATED_DATE}>{language === 'he' ? '19 בספטמבר 2026' : '19 September 2026'}</time></p>
      <p className="legal-intro">{copy.intro}</p>
    </header>
    <nav className="legal-contents" aria-label={t('On this page')}>
      <p>{t('On this page')}</p>
      <ul>{copy.sections.map(section => <li key={section.id}><a href={`#${section.id}`}>{section.title}</a></li>)}</ul>
    </nav>
    <div className="legal-body">
      {copy.sections.map(section => <section key={section.id} id={section.id} aria-labelledby={`${section.id}-title`}>
        <h2 id={`${section.id}-title`} tabIndex={-1}>{section.title}</h2>
        {section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}
        {page === 'privacy' && section.id === 'retention' && <>
          {info ? <RetentionDetails info={info} /> : <p role="status">{t(status === 'loading' ? 'Loading the server’s current retention settings…' : 'Current retention settings are unavailable. Please retry before submitting personal information.')}</p>}
          {status === 'unavailable' && <button className="ghost-button" type="button" onClick={retry}>{t('Try again')}</button>}
        </>}
        {section.id === 'providers' && <ul className="legal-links">
          <li><a href="https://render.com/privacy">Render · {t('Privacy')}</a></li>
          <li><a href="https://neon.com/privacy-policy">Neon · {t('Privacy')}</a></li>
          <li><a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement">GitHub · {t('Privacy')}</a></li>
        </ul>}
        {section.id === 'ip' && <p><a href="https://github.com/yairrrr/MiZeMi/blob/main/backend/app/data/knowledge/LICENSES.md">{t('Reference data licenses and attribution')}</a>{' · '}<a href="/THIRD_PARTY_NOTICES.txt">{t('Third-party software notices')}</a></p>}
        {(section.id === 'requests' || section.id === 'contact' || section.id === 'report') && <ContactDetails />}
      </section>)}
    </div>
    <a className="legal-back" href="/">{t('Back to MiZeMi')}</a>
  </article>
}
