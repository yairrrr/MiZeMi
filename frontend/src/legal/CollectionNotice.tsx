import { useI18n } from '../i18n/I18n'
import type { PrivacyInfo } from './privacyInfo'
import { ContactDetails } from './ContactDetails'

export function CollectionNotice({ info }: { info: PrivacyInfo | null }) {
  const { t, language } = useI18n()
  return <section className="collection-notice" aria-labelledby="collection-notice-title">
    <h3 id="collection-notice-title">{t('Before you share')}</h3>
    <p id="question-use-help">{t('Everything you fill in here is sent to the game server. Only answers you tick are used to create questions, and the game may combine them with general facts or compare them with other players. Unticked answers still reach the server but are not used for questions.')}</p>
    <p>{t('Ticked answers may appear in questions, answers and explanations that the whole group sees. Only share what you are happy for the group to know.')}</p>
    {info && <p>{t('Your profile is deleted from the server when the game ends. The game results (names, questions, answers and scores) are kept for about {days} days and then deleted. Questions may include information you ticked.', { days: info.retention_days })}</p>}
    <p>{t('You cannot edit your profile after sending it. Optional fields can stay blank. If you do not want to fill in the required fields, simply do not join the game.')}</p>
    <ContactDetails compact />
    <a href={`/privacy?lang=${language}`} target="_blank" rel="noopener noreferrer">{t('Read the full Privacy Policy')}<span className="sr-only">{t(' (opens in a new tab)')}</span></a>
  </section>
}
