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
  label: string
  kind: 'text' | 'int' | 'choice'
  required: boolean
  maxLength?: number
  min?: number
  max?: number
  choices?: readonly string[]
  placeholder?: string
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
): { fields: ProfileField[] } | { error: string } {
  const fields: ProfileField[] = []
  for (const spec of PROFILE_FIELDS) {
    const raw = (values[spec.key] ?? '').trim().replace(/\s+/g, ' ')
    if (raw === '') {
      if (spec.required) {
        return { error: `${spec.label} is required.` }
      }
      continue
    }

    let value: string | number = raw
    if (spec.kind === 'int') {
      if (!/^\d+$/.test(raw)) {
        return { error: `${spec.label} must be a whole number.` }
      }
      value = Number(raw)
      if (value < (spec.min ?? 0) || value > (spec.max ?? Number.MAX_SAFE_INTEGER)) {
        return { error: `${spec.label} must be between ${spec.min} and ${spec.max}.` }
      }
    } else if (spec.kind === 'choice') {
      if (!spec.choices?.includes(raw)) {
        return { error: `Choose one of the listed options for ${spec.label}.` }
      }
    } else {
      if (raw.length > (spec.maxLength ?? Infinity)) {
        return { error: `${spec.label} must be at most ${spec.maxLength} characters.` }
      }
      if (EMAIL.test(raw) || LINK.test(raw) || LONG_NUMBER.test(raw)) {
        return { error: PRIVACY_MESSAGE }
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
