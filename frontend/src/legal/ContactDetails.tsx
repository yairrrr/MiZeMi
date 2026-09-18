import { useI18n } from '../i18n/I18n'

// No private Git author address is repurposed as a public support address.
// Replace this disclosure only after the operator supplies an authorized channel.
export function ContactDetails() {
  const { language } = useI18n()
  return language === 'he' ? <>
    <p>טרם פורסם ערוץ קשר פרטי ייעודי עם מפעיל הפרויקט. בהדגמה מתואמת, פנו לאדם שהזמין אתכם דרך ערוץ פרטי שכבר קיים ביניכם ובקשו ממנו להעביר למפעיל שאלה בנושא פרטיות או נגישות. אם אין לכם דרך להגיע למפעיל, הימנעו משליחת מידע אישי אמיתי.</p>
    <p>אפשר לבקש בירור, גישה למידע שלכם, תיקון או מחיקה, לפי הדין והנסיבות. לפני טיפול במידע יש לוודא את זהות הפונה ואת הקשר שלו למשחק; קוד חדר או שם לתצוגה לבדם אינם הוכחת זהות. אל תפרסמו מידע אישי, אסימוני כניסה או פרטי משתתפים בבעיית GitHub ציבורית. אין כרגע טופס בקשות או שירות תמיכה עם זמן מענה מובטח.</p>
    <p>פרסום ערוץ קשר פרטי ופרטי מפעיל מתאימים נדרש לפני הרחבת השירות לציבור. עצם הצגת העמוד הזה אינה מעידה שבקשה הוגשה או טופלה.</p>
  </> : <>
    <p>A dedicated private contact channel for the project operator has not yet been published. For an arranged demonstration, contact the person who invited you through an existing private channel and ask them to forward a privacy or accessibility question to the operator. If you cannot reach the operator, avoid submitting real personal information.</p>
    <p>You can ask about access to your information, correction or deletion, subject to applicable law and the circumstances. Handling personal records requires verifying the requester and their connection to the game; a room code or display name alone is not proof of identity. Do not post personal information, session tokens or other players’ details in a public GitHub issue. There is currently no request form or guaranteed support response time.</p>
    <p>An appropriate private contact channel and operator details must be published before broader public use. Displaying this page does not mean a request has been submitted or handled.</p>
  </>
}
