import { useI18n } from '../i18n/I18n'
import type { PrivacyInfo } from './privacyInfo'
import { RetentionDetails } from './RetentionDetails'

export function CollectionNotice({ info }: { info: PrivacyInfo | null }) {
  const { t, language } = useI18n()
  return <section className="collection-notice" aria-labelledby="collection-notice-title">
    <h3 id="collection-notice-title">{t('Before you share')}</h3>
    <p>{t('Your submitted information goes to the game server to run this group game. Fields enabled for questions may be matched to offline facts and classified to create questions, including group comparisons. A disabled field does not influence question generation or derived reasoning.')}</p>
    <p id="question-use-help">{t('Question-use choices control question generation, not whether the server receives your submitted profile. Other players may see enabled information in questions, answers and explanations. Only share what you are comfortable discussing with the group.')}</p>
    {info && <RetentionDetails info={info} compact />}
    <p>{t('Profiles cannot currently be edited after submission. Optional fields may be left blank; if you do not wish to submit the required fields, do not join the game.')}</p>
    <p>{t('Only use real personal information if your organizer has given you a private way to reach the operator.')}</p>
    <a href={`/privacy?lang=${language}`} target="_blank" rel="noopener noreferrer">{t('Read the full Privacy Policy')}<span className="sr-only">{t(' (opens in a new tab)')}</span></a>
  </section>
}
