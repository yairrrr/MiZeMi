import { translate, type MessageKey, type Translate } from '../../i18n/messages'
import type { ProfileField } from '../../types'

// Mirror of the server's profile schema (MASTER_SPEC.md §9.2; backend
// app/application/profile_rules.py). The server re-validates everything —
// this copy only gives players instant, friendly feedback.

export const MUSIC_STYLES = [
  'Pop',
  'Rock',
  'Hip-Hop / Rap',
  'Electronic',
  'Mizrahi',
  'Classical',
  'Jazz',
  'Metal',
  'Other',
] as const

export type ProfileFieldSpec = {
  key: string
  label: MessageKey
  kind: 'text' | 'int' | 'choice'
  required: boolean
  maxLength?: number
  min?: number
  max?: number
  choices?: readonly MessageKey[]
  placeholder?: MessageKey
  /** Initial consent. Personal facts start opted out (§10.2). */
  defaultAllow: boolean
}

export const PROFILE_FIELDS: readonly ProfileFieldSpec[] = [
  { key: 'city', label: 'City', kind: 'text', required: true, maxLength: 40, placeholder: 'Where do you live?', defaultAllow: true },
  { key: 'favorite_food', label: 'Favorite food', kind: 'text', required: true, maxLength: 40, placeholder: 'e.g. pizza', defaultAllow: true },
  { key: 'hobby', label: 'Hobby', kind: 'text', required: true, maxLength: 40, placeholder: 'e.g. rock climbing', defaultAllow: true },
  { key: 'favorite_music', label: 'Favorite music style', kind: 'choice', required: true, choices: MUSIC_STYLES, defaultAllow: true },
  { key: 'age', label: 'Age', kind: 'int', required: false, min: 5, max: 120, placeholder: 'Optional', defaultAllow: true },
  { key: 'favorite_movie', label: 'Favorite movie', kind: 'text', required: false, maxLength: 60, placeholder: 'Optional', defaultAllow: true },
  { key: 'personal_fact', label: 'Something interesting about me', kind: 'text', required: false, maxLength: 120, placeholder: 'Optional fun fact', defaultAllow: false },
]

const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/
const LINK = /(https?:\/\/|www\.)/i
const LONG_NUMBER = /\d(?:[\s\-.]?\d){6,}/

export const PRIVACY_MESSAGE =
  "Please don't include contact details, links, or ID/phone numbers in your profile."

export type ProfileFormValues = Record<string, string>
export type ProfileConsent = Record<string, boolean>

export function initialConsent(): ProfileConsent {
  return Object.fromEntries(PROFILE_FIELDS.map((field) => [field.key, field.defaultAllow]))
}

/** Build the wire field list, or return the first problem to show the player. */
export function buildProfileFields(
  values: ProfileFormValues,
  consent: ProfileConsent,
  t: Translate = (key, values) => translate('en', key, values),
): { fields: ProfileField[] } | { error: string } {
  const fields: ProfileField[] = []
  for (const spec of PROFILE_FIELDS) {
    const raw = (values[spec.key] ?? '').trim().replace(/\s+/g, ' ')
    if (raw === '') {
      if (spec.required) {
        return { error: t('{field} is required.', { field: t(spec.label) }) }
      }
      continue
    }

    let value: string | number = raw
    if (spec.kind === 'int') {
      if (!/^\d+$/.test(raw)) {
        return { error: t('{field} must be a whole number.', { field: t(spec.label) }) }
      }
      value = Number(raw)
      if (value < (spec.min ?? 0) || value > (spec.max ?? Number.MAX_SAFE_INTEGER)) {
        return { error: t('{field} must be between {min} and {max}.', { field: t(spec.label), min: spec.min!, max: spec.max! }) }
      }
    } else if (spec.kind === 'choice') {
      if (!spec.choices?.some((choice) => choice === raw)) {
        return { error: t('Choose one of the listed options for {field}.', { field: t(spec.label) }) }
      }
    } else {
      if (raw.length > (spec.maxLength ?? Infinity)) {
        return { error: t('{field} must be at most {max} characters.', { field: t(spec.label), max: spec.maxLength! }) }
      }
      if (EMAIL.test(raw) || LINK.test(raw) || LONG_NUMBER.test(raw)) {
        return { error: t(PRIVACY_MESSAGE) }
      }
    }

    fields.push({
      field_key: spec.key,
      value,
      allow_question_usage: consent[spec.key] ?? spec.defaultAllow,
    })
  }
  return { fields }
}
