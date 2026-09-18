import { useI18n } from '../i18n/I18n'
import type { PrivacyInfo } from './privacyInfo'

export function RetentionDetails({ info, compact = false }: { info: PrivacyInfo; compact?: boolean }) {
  const { t } = useI18n()
  return <>
    <p>{t('Raw profile fields stay in server memory during play and are cleared when the game finishes. New finished-game database records do not include raw profile fields, whether question use was enabled or disabled.')}</p>
    <p>{t('Finished records keep display names, game questions and explanations, answers, scores and game details. Consented information may therefore remain in the generated game content.')}</p>
    <p>{t('Finished database records become eligible for deletion after {days} days from their last save. Cleanup runs at startup and every {minutes} minutes while the service is running, in bounded batches. Outages or a backlog can delay deletion.', { days: info.retention_days, minutes: info.maintenance_interval_seconds / 60 })}</p>
    {!compact && <>
      <p>{t('Rooms with no connected participants expire after {minutes} minutes of inactivity, checked during cleanup. Connected rooms can keep game content in memory until they close or the server restarts. Leaving a room does not immediately erase its result record.', { minutes: info.room_idle_ttl_minutes })}</p>
      <p>{t('Older saved profiles are removed by the same bounded maintenance process. Provider logs and backups may have different retention; deleting live records does not promise immediate deletion from every backup. Active rooms cannot be recovered after a server restart.')}</p>
    </>}
  </>
}
