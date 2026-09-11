import { useI18n } from '../i18n/I18n'

/** Text and links only: no remote assets, tracking, fetches or HTML injection. */
export function KnowledgeCredits() {
  const { t } = useI18n()
  return (
    <details className="knowledge-credits">
      <summary>{t('How the connections work')}</summary>
      <p>{t('The game connects the answers you agreed to share with facts about films, music, food, hobbies and towns.')}</p>
      <p>{t('Distances compare towns by air, not home addresses or driving routes.')}</p>
      <p>{t('Facts from Wikidata (CC0). Place data from GeoNames (CC BY 4.0), filtered and adapted by MiZeMi.')}</p>
      <nav aria-label={t('Reference credits')}>
        <a href="https://www.wikidata.org/wiki/Wikidata:Licensing" target="_blank" rel="noreferrer">Wikidata · CC0</a>
        {' · '}
        <a href="https://www.geonames.org/" target="_blank" rel="noreferrer">GeoNames</a>
        {' · '}
        <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noreferrer">CC BY 4.0</a>
      </nav>
    </details>
  )
}
