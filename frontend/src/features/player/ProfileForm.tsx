import { useI18n } from '../../i18n/I18n'
import { type FormEvent, useEffect, useState } from 'react'

import type { SendFn } from '../../hooks/useGameConnection'
import type { ErrorResponse } from '../../types'
import {
  buildProfileFields,
  initialConsent,
  PROFILE_FIELDS,
  type ProfileConsent,
  type ProfileFormValues,
} from './profileSchema'

export function ProfileForm({
  playerId,
  displayName,
  send,
  serverError,
  connected = true,
}: {
  playerId: string
  displayName: string
  send: SendFn
  serverError: ErrorResponse['error'] | null
  connected?: boolean
}) {
  const { t } = useI18n()
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
    const result = buildProfileFields(values, consent)
    if ('error' in result) {
      setError('validation')
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
        <p className="card-copy">{t("Your answers become the questions. Uncheck “Use in questions” for anything you’d rather keep to yourself.")}</p>
      </div>

      {PROFILE_FIELDS.map((spec) => {
        const inputId = `profile-${spec.key}`
        return (
          <div key={spec.key} className="profile-field">
            <label htmlFor={inputId}>
              {t(spec.label)}
              {spec.required ? '' : t(' (optional)')}
            </label>
            {spec.kind === 'choice' ? (
              <select
                id={inputId}
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
            ) : (
              <input
                id={inputId}
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
            <label className="consent-toggle">
              <input
                type="checkbox"
                checked={consent[spec.key] ?? spec.defaultAllow}
                disabled={submitting}
                onChange={(event) => setConsent({ ...consent, [spec.key]: event.target.checked })}
                aria-label={t('Use {field} in questions', { field: t(spec.label) })}
              />{t("Use in questions")}</label>
          </div>
        )
      })}

      <p className="privacy-hint">{t("Keep it fun and light: no passwords, ID numbers, addresses, phone numbers, emails, or anything secret.")}</p>

      {error !== null && (
        <p className="status-message error-message" role="alert">
          {error === 'connection' ? t('Still connecting — please try again in a second.') : validation && 'error' in validation ? validation.error : null}
        </p>
      )}

      <button type="submit" className="primary-button join-button" disabled={submitting}>
        {t(submitting ? 'Saving…' : 'Save my profile')}
      </button>
    </form>
  )
}
