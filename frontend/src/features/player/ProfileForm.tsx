import { CollectionNotice } from '../../legal/CollectionNotice'
import { usePrivacyInfo } from '../../legal/privacyInfo'
import { useI18n } from '../../i18n/I18n'
import { type FormEvent, useEffect, useState } from 'react'

import type { SendFn } from '../../hooks/useGameConnection'
import type { ErrorResponse, QuestionSource } from '../../types'
import {
  buildProfileFields,
  initialConsent,
  PROFILE_FIELDS,
  type ProfileConsent,
  type ProfileFormValues,
} from './profileSchema'
import { SuggestInput } from './SuggestInput'

export function ProfileForm({
  playerId,
  displayName,
  send,
  serverError,
  connected = true,
  questionSource = 'algorithmic',
}: {
  playerId: string
  displayName: string
  send: SendFn
  serverError: ErrorResponse['error'] | null
  connected?: boolean
  questionSource?: QuestionSource
}) {
  const { t } = useI18n()
  const privacy = usePrivacyInfo()
  const [values, setValues] = useState<ProfileFormValues>({})
  const [consent, setConsent] = useState<ProfileConsent>(initialConsent)
  const [error, setError] = useState<'validation' | 'connection' | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    // A server rejection re-opens the form for correction.
    if (serverError !== null || !connected) {
      setSubmitting(false)
    }
  }, [serverError, connected])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (privacy.status !== 'ready') return
    const result = buildProfileFields(values, consent)
    if ('error' in result) {
      setError('validation')
      document.getElementById(`profile-${result.fieldKey}`)?.focus()
      return
    }
    setError(null)
    if (send('player.profile_submit', { player_id: playerId, fields: result.fields })) {
      setSubmitting(true)
    } else {
      setError('connection')
    }
  }

  const validation = error === 'validation' ? buildProfileFields(values, consent, t) : null
  return (
    <form className="stage profile-form" onSubmit={handleSubmit} noValidate aria-labelledby="profile-title">
      <div>
        <p className="eyebrow">{t('You’re in, {name}!', { name: displayName })}</p>
        <h2 id="profile-title">{t("Tell the group about you")}</h2>
        <p className="card-copy">{t("Choose which answers may influence game questions. Unchecking a field does not prevent the server from receiving it.")}</p>
      </div>

      {PROFILE_FIELDS.map((spec) => {
        const inputId = `profile-${spec.key}`
        const fieldError = validation && 'error' in validation && validation.fieldKey === spec.key ? validation.error : null
        const accessibleInput = {
          required: spec.required, 'aria-required': spec.required,
          'aria-invalid': fieldError ? true as const : undefined,
          'aria-describedby': fieldError ? `${inputId}-error` : undefined,
        }
        return (
          <div key={spec.key} className="profile-field">
            <label htmlFor={inputId}>
              {t(spec.label)}
              {spec.required ? '' : t(' (optional)')}
            </label>
            {spec.kind === 'choice' ? (
              <select
                id={inputId}
                {...accessibleInput}
                dir="auto"
                value={values[spec.key] ?? ''}
                disabled={submitting}
                onChange={(event) => setValues({ ...values, [spec.key]: event.target.value })}
              >
                <option value="">{t("Choose…")}</option>
                {spec.choices?.map((choice) => (
                  <option key={choice} value={choice}>
                    {t(choice)}
                  </option>
                ))}
              </select>
            ) : spec.suggest ? (
              <SuggestInput
                id={inputId}
                field={spec.key}
                {...accessibleInput}
                dir="auto"
                value={values[spec.key] ?? ''}
                maxLength={spec.maxLength}
                placeholder={spec.placeholder ? t(spec.placeholder) : undefined}
                autoComplete="off"
                disabled={submitting}
                onValueChange={(value) => setValues((current) => ({ ...current, [spec.key]: value }))}
              />
            ) : (
              <input
                id={inputId}
                {...accessibleInput}
                dir="auto"
                value={values[spec.key] ?? ''}
                inputMode={spec.kind === 'int' ? 'numeric' : 'text'}
                maxLength={spec.kind === 'int' ? 3 : spec.maxLength}
                placeholder={spec.placeholder ? t(spec.placeholder) : undefined}
                autoComplete="off"
                disabled={submitting}
                onChange={(event) => setValues({ ...values, [spec.key]: event.target.value })}
              />
            )}
            {fieldError && <p id={`${inputId}-error`} className="field-error">{fieldError}</p>}
            <label className="consent-toggle">
              <input
                type="checkbox"
                checked={consent[spec.key] ?? spec.defaultAllow}
                disabled={submitting}
                onChange={(event) => setConsent({ ...consent, [spec.key]: event.target.checked })}
                aria-label={t('Allow {field} to be used for game questions', { field: t(spec.label) })}
                aria-describedby="question-use-help"
              />{t('Allow {field} to be used for game questions', { field: t(spec.label) })}</label>
          </div>
        )
      })}

      <CollectionNotice info={privacy.info} />

      {questionSource === 'ai' && (
        <p className="privacy-hint ai-notice" role="note" style={{ borderLeft: '3px solid #6547cb', paddingLeft: '0.75rem' }}>
          ⚡ {t('AI mode is on for this room. Your ticked answers will be sent to Anthropic over TLS so Claude can craft group questions. Unticked answers never leave the server.')}
        </p>
      )}

      <p className="privacy-hint">{t("Keep it fun and light: no passwords, ID numbers, addresses, phone numbers, emails, or anything secret.")}</p>

      {error !== null && (
        <p className="status-message error-message" role="alert">
          {error === 'connection' ? t('Still connecting — please try again in a second.') : validation && 'error' in validation ? validation.error : null}
        </p>
      )}

      {privacy.status !== 'ready' && <div className="policy-availability">
        <p role="status">{t(privacy.status === 'loading' ? 'Loading the server’s current retention settings…' : 'Current retention settings are unavailable. Please retry before submitting personal information.')}</p>
        {privacy.status === 'unavailable' && <button type="button" className="ghost-button" onClick={privacy.retry}>{t('Try again')}</button>}
      </div>}
      <button type="submit" className="primary-button join-button" disabled={submitting || privacy.status !== 'ready'}>
        {t(submitting ? 'Saving…' : 'Save my profile')}
      </button>
    </form>
  )
}
