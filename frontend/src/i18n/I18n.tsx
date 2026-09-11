import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { ErrorResponse } from '../types'
import { translate, type Language, type Translate } from './messages'

export const LANGUAGE_STORAGE_KEY = 'mizemi.language'
export const direction = (language: Language) => language === 'he' ? 'rtl' : 'ltr'

export function loadLanguage(): Language {
  try { return window.localStorage.getItem(LANGUAGE_STORAGE_KEY) === 'he' ? 'he' : 'en' }
  catch { return 'en' }
}

const errors: Record<ErrorResponse['error']['code'], string> = {
  ROOM_NOT_FOUND: 'לא נמצא חדר עם הקוד הזה.',
  ROOM_FULL: 'החדר או השרת מלאים כרגע. נסו שוב בהמשך.',
  NAME_TAKEN: 'השם הזה כבר תפוס בחדר. בחרו שם אחר.',
  INVALID_STATE_TRANSITION: 'אי אפשר לבצע את הפעולה בשלב הזה של המשחק.',
  QUESTION_CLOSED: 'הזמן נגמר או שהשאלה כבר נסגרה.',
  ALREADY_ANSWERED: 'התשובה שלך לשאלה הזאת כבר נקלטה.',
  NOT_HOST: 'רק המארח יכול לבצע את הפעולה הזאת.',
  VALIDATION_ERROR: 'חלק מהפרטים אינם תקינים. בדקו את השדות ונסו שוב.',
  UNKNOWN_EVENT: 'הפעולה אינה מוכרת. נסו לרענן את הדף.',
  INTERNAL_ERROR: 'השרת לא זמין כרגע. ייתכן שהוא מתעורר — נסו שוב בעוד רגע.',
  ROOM_NOT_JOINABLE: 'המשחק כבר התחיל ולא ניתן להצטרף אליו.',
  NO_QUESTIONS_AVAILABLE: 'אין מספיק מידע מאושר ליצירת שאלות. פתחו חדר חדש ושתפו עוד פרטים עם הרשאה לשימוש בשאלות.',
}

export function publicError(language: Language, error: ErrorResponse['error']): string {
  return language === 'he' ? (errors[error.code] ?? errors.INTERNAL_ERROR) : error.message
}

type I18n = {
  language: Language
  setLanguage: (language: Language) => void
  t: Translate
  number: (value: number) => string
}
const Context = createContext<I18n>({
  language: 'en', setLanguage: () => {}, t: (key, values) => translate('en', key, values),
  number: (value) => value.toLocaleString('en-US'),
})

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setSelected] = useState<Language>(loadLanguage)
  function setLanguage(next: Language) {
    setSelected(next)
    try { window.localStorage.setItem(LANGUAGE_STORAGE_KEY, next) } catch { /* page still works */ }
  }
  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dir = direction(language)
  }, [language])
  useEffect(() => {
    const changed = (event: StorageEvent) => {
      if (event.key === LANGUAGE_STORAGE_KEY) setSelected(loadLanguage())
    }
    window.addEventListener('storage', changed)
    return () => window.removeEventListener('storage', changed)
  }, [])
  return <Context.Provider value={{ language, setLanguage,
    t: (key, values) => translate(language, key, values),
    number: (value) => value.toLocaleString(language === 'he' ? 'he-IL' : 'en-US'),
  }}>{children}</Context.Provider>
}

export const useI18n = () => useContext(Context)

export function LanguageSelector() {
  const { language, setLanguage, t } = useI18n()
  return <div className="language-bar">
    <label htmlFor="ui-language">{t('Language')}</label>
    <select id="ui-language" value={language} onChange={(e) => setLanguage(e.target.value === 'he' ? 'he' : 'en')}>
      <option value="en" lang="en">English</option>
      <option value="he" lang="he">עברית</option>
    </select>
  </div>
}
