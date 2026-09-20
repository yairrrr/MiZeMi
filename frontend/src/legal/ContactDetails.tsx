import { useI18n } from '../i18n/I18n'

export const PUBLIC_OPERATORS = ['yairrrr', 'gavrielalafi-boop', 'urielmizrahi91-svg', 'elick-chitrit'] as const
export const CONTACT_URL = 'https://github.com/yairrrr/MiZeMi/issues'

// Owner-approved public identities and initial-contact route; never a private inbox.
export const contactCopy = {
  en: {
    operator: 'Project operator:',
    introduction: 'For privacy questions, access, correction/deletion or accessibility requests, start with a non-sensitive message on',
    link: 'MiZeMi GitHub Issues',
    warning: 'Treat Issues as public: your GitHub username, message and attachments may be visible to others. Do not post personal or sensitive information, profile answers, room/player identifiers, credentials, identity documents or identifying screenshots.',
    initial: 'For a request involving personal information, post only this initial message: “I would like to contact the operator about a privacy request.” Do not include the request details.',
    private: 'Any necessary personal details or identity verification must wait until a suitable private channel has been agreed with the operator. Public Issues alone cannot complete a request that requires confidential information. This page does not provide a private channel.',
    access: 'A GitHub account and access to the repository are required. If the Issues page is unavailable to you, this contact route cannot be used. For an arranged demonstration, you may use an existing private organizer contact. Do not publish personal information to work around an access problem.',
    compact: 'Use Issues only for an initial non-sensitive message. Do not post personal information, profile answers, room/player identifiers or credentials. Personal details and identity verification require a separately agreed private channel; Issues is not that channel. A GitHub account and repository access are required.',
  },
  he: {
    operator: 'מפעיל הפרויקט:',
    introduction: 'לשאלות פרטיות, לבקשות גישה למידע, תיקון או מחיקה, או לפניות בנושא נגישות, התחילו בהודעה שאינה מכילה מידע רגיש בעמוד',
    link: 'הפניות של MiZeMi ב־GitHub',
    warning: 'התייחסו לפניות כאל פרסום ציבורי: שם המשתמש שלכם, ההודעה והקבצים המצורפים עשויים להיות גלויים לאחרים. אל תפרסמו מידע אישי או רגיש, תשובות מהפרופיל, מזהי חדר או משתתף, אישורי כניסה, מסמכי זיהוי או צילומי מסך מזהים.',
    initial: 'לבקשה הכרוכה במידע אישי, פרסמו רק את הודעת הפתיחה הזאת: ״ברצוני ליצור קשר עם המפעיל בנוגע לבקשת פרטיות.״ אל תכללו את פרטי הבקשה.',
    private: 'יש להמתין עם מסירת פרטים אישיים או אימות זהות עד לתיאום ערוץ פרטי מתאים עם המפעיל. אי אפשר להשלים בפנייה ציבורית בלבד בקשה המחייבת מידע חסוי. עמוד זה אינו מספק ערוץ פרטי.',
    access: 'נדרשים חשבון GitHub והרשאת גישה למאגר. אם עמוד הפניות אינו זמין לכם, אי אפשר להשתמש בדרך הקשר הזאת. בהדגמה מתואמת אפשר להשתמש בערוץ פרטי קיים מול המארגן. אל תפרסמו מידע אישי כדי לעקוף בעיית גישה.',
    compact: 'השתמשו בעמוד הפניות רק להודעה ראשונית שאינה מכילה מידע רגיש. אל תפרסמו מידע אישי, תשובות מהפרופיל, מזהי חדר או משתתף, או אישורי כניסה. מסירת פרטים אישיים ואימות זהות דורשים ערוץ פרטי שתואם בנפרד; עמוד הפניות אינו ערוץ כזה. נדרשים חשבון GitHub והרשאת גישה למאגר.',
  },
} as const

export function ContactDetails({ compact = false }: { compact?: boolean }) {
  const { language, t } = useI18n()
  const copy = contactCopy[language]
  return <div className="contact-details">
    <p>{copy.operator} <bdi>{PUBLIC_OPERATORS.join(', ')}</bdi></p>
    <p>{copy.introduction}{' '}<a href={CONTACT_URL} target="_blank" rel="noopener noreferrer">{copy.link}<span className="sr-only">{t(' (opens in a new tab)')}</span></a>.</p>
    {compact ? <p>{copy.compact}</p> : <>
      <p>{copy.warning}</p>
      <p>{copy.initial}</p>
      <p>{copy.private}</p>
      <p>{copy.access}</p>
    </>}
  </div>
}
