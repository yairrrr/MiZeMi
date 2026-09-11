import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { hebrew, translate, type MessageKey } from './messages'
import { I18nProvider, LANGUAGE_STORAGE_KEY, LanguageSelector, loadLanguage, publicError } from './I18n'
import { App } from '../components/App'
import { HostGameView } from '../features/host/HostGame'
import { PlayerGameView } from '../features/player/PlayerGame'
import { ProfileForm } from '../features/player/ProfileForm'
import { initialGameView } from '../state/gameReducer'
import { ERROR_CODES, type RoomSnapshot, type Question, type QuestionEnded } from '../types'
import type { SendFn } from '../hooks/useGameConnection'
import type { PlayerProfile } from '../types'
import { createRoom } from '../api/roomApi'

vi.mock('../api/roomApi', async (importOriginal) => ({ ...await importOriginal<typeof import('../api/roomApi')>(), createRoom: vi.fn() }))
vi.mock('../hooks/useGameConnection', () => ({ useGameConnection: () => ({ view: initialGameView, status: 'connecting', send: () => true, dismissError: () => {} }) }))

beforeEach(() => { window.localStorage.clear(); sessionStorage.clear(); vi.mocked(createRoom).mockReset() })
afterEach(() => { cleanup(); window.localStorage.clear(); sessionStorage.clear(); document.documentElement.dir = 'ltr'; document.documentElement.lang = 'en' })

test.each(Object.keys(hebrew) as MessageKey[])('translation is complete and keeps placeholders: %s', (key) => {
  const original = [...key.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
  const translated = [...hebrew[key].matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort()
  expect(translated).toEqual(original)
  expect(hebrew[key]).toMatch(/[א-ת]/)
  expect(translate('en', key)).toBe(key)
})

test('switches the whole document to Hebrew, persists selection, and restores it', async () => {
  const user=userEvent.setup()
  render(<App />)
  expect(document.documentElement).toHaveAttribute('dir','ltr')
  await user.selectOptions(screen.getByLabelText('Language'),'he')
  expect(document.documentElement).toHaveAttribute('lang','he')
  expect(document.documentElement).toHaveAttribute('dir','rtl')
  expect(screen.getByRole('button',{name:'יצירת חדר'})).toBeVisible()
  expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('he')
  cleanup()
  render(<App />)
  expect(screen.getByLabelText('שפה')).toHaveValue('he')
  await user.selectOptions(screen.getByLabelText('שפה'),'en')
  expect(document.documentElement).toHaveAttribute('dir','ltr')
})

test('unsupported stored locale falls back safely', () => {
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY,'../../templates')
  expect(loadLanguage()).toBe('en')
})

test('home logo is accessible and count is visibly twenty', () => {
  render(<App />)
  expect(screen.getByRole('img',{name:'MiZeMi'})).toHaveAttribute('src',expect.stringContaining('mizemi-logo.png'))
  expect(screen.getByRole('heading',{level:1,name:'MiZeMi'})).toBeVisible()
  expect(screen.getByLabelText('Number of questions')).toHaveValue(20)
})

test('selected custom count and independent game language reach the API', async () => {
  vi.mocked(createRoom).mockReturnValue(new Promise(() => {}))
  render(<App />)
  const user=userEvent.setup()
  await user.clear(screen.getByLabelText('Number of questions'))
  await user.type(screen.getByLabelText('Number of questions'),'7')
  await user.selectOptions(screen.getByLabelText('Game language'),'he')
  await user.click(screen.getByRole('button',{name:'Create Room'}))
  expect(createRoom).toHaveBeenCalledWith({question_count:7,language:'he'})
  expect(document.documentElement).toHaveAttribute('lang','en')
})

test('default count and Hebrew UI default reach API unchanged', async () => {
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY,'he')
  vi.mocked(createRoom).mockReturnValue(new Promise(() => {}))
  render(<App />)
  await userEvent.click(screen.getByRole('button',{name:'יצירת חדר'}))
  expect(createRoom).toHaveBeenCalledWith({question_count:20,language:'he'})
})

test.each(['0','-1','51','2.5',''])('invalid question count %s never calls create', async (value) => {
  render(<App />)
  const user=userEvent.setup()
  await user.clear(screen.getByLabelText('Number of questions'))
  if (value) await user.type(screen.getByLabelText('Number of questions'),value)
  await user.click(screen.getByRole('button',{name:'Create Room'}))
  expect(createRoom).not.toHaveBeenCalled()
  expect(screen.getByRole('alert')).toHaveTextContent('Choose a whole number from 1 to 50.')
})

test.each(ERROR_CODES)('public error %s has a safe Hebrew message', (code) => {
  const message=publicError('he',{code,message:'PRIVATE_ENGLISH_SENTINEL'})
  expect(message).toMatch(/[א-ת]/)
  expect(message).not.toContain('SENTINEL')
})

const host={role:'host' as const,room_code:'ABC234',game_id:'g',host_token:'local-test-token'}
const player={role:'player' as const,room_code:'ABC234',game_id:'g',player_id:'p',player_token:'local-test-token',display_name:'דנה'}
const person={player_id:'p',display_name:'דנה',is_host:false,connected:true,has_profile:true,is_ready:true,score:900}
const room:RoomSnapshot={room_code:'ABC234',state:'READY',players:[person],current_question_index:0,total_questions:5,config:{question_count:5,language:'he'}}
const q:Question={question_id:'q',index:0,total_questions:5,question_type:'multiple_choice',difficulty:'HARD',language:'he',text:'מי בחר פיצה?',options:[{option_id:'a',text:'דנה'},{option_id:'b',text:'Noa'}],time_limit_seconds:20,started_at:new Date().toISOString()}
const ended:QuestionEnded={explanation:'המסור ולזמן את הרוע הם סרטי אימה.',question_id:'q',text:q.text,options:q.options,difficulty:'HARD',language:'he',correct_option_id:'a',statistics:{question_id:'q',correct_option_id:'a',answer_distribution:[{option_id:'a',count:1,percentage:100},{option_id:'b',count:0,percentage:0}],answered_count:1,player_count:1},player_result:{option_id:'a',is_correct:true,points_awarded:900,total_score:900}}
const board=[{player_id:'p',display_name:'דנה',rank:1,total_score:900}]
const view={...initialGameView,room,question:q,results:ended,leaderboard:board,finished:{leaderboard:{entries:board},winners:board}}
const callbacks={send:vi.fn(() => true),dismissError:()=>{},onLeave:()=>{},status:'open' as const}

test.each(['READY','QUESTION_ACTIVE','QUESTION_RESULTS','LEADERBOARD','FINISHED'] as const)('both Hebrew game screens translate the %s stage', (state) => {
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY,'he')
  const current={...view,room:{...room,state}}
  const rendered=render(<I18nProvider><HostGameView session={host} view={current} {...callbacks}/><PlayerGameView session={player} view={current} {...callbacks}/></I18nProvider>)
  expect(rendered.container.textContent).toMatch(/[א-ת]/)
  for (const text of ['Start game','Correct answer:','Show leaderboard','Next question','Final leaderboard','Play again','points','Your answer']) {
    expect(rendered.container.textContent).not.toContain(text)
  }
  if (state==='QUESTION_ACTIVE') {
    expect(screen.queryByText(ended.explanation!)).toBeNull()
    expect(screen.getAllByText('שאלה 1 מתוך 5')).toHaveLength(2)
    expect(screen.getAllByRole('heading',{name:q.text})[0]).toHaveAttribute('dir','rtl')
  }
  if (state==='QUESTION_RESULTS') {
    for (const explanation of screen.getAllByText(ended.explanation!)) {
      expect(explanation).toHaveAttribute('lang','he')
      expect(explanation).toHaveAttribute('dir','rtl')
    }
    expect(screen.getByText('+900')).toHaveAttribute('dir','ltr')
    expect(rendered.container.querySelector('.verdict')).toHaveTextContent('+900 נקודות')
  }
})

test('UI switching preserves the shared question language and user values', async () => {
  render(<I18nProvider><LanguageSelector/><PlayerGameView session={player} view={{...view,room:{...room,state:'QUESTION_ACTIVE'}}} {...callbacks}/></I18nProvider>)
  expect(screen.getByRole('heading',{name:q.text})).toHaveAttribute('dir','rtl')
  await userEvent.selectOptions(screen.getByLabelText('Language'),'he')
  expect(screen.getByRole('heading',{name:q.text})).toHaveTextContent(q.text)
  expect(screen.getByText('Noa')).toBeVisible()
})

test('Hebrew profile labels, validation, consent and music choices keep stable wire values', async () => {
  window.localStorage.setItem(LANGUAGE_STORAGE_KEY,'he')
  const send=vi.fn<SendFn>(() => true)
  const user=userEvent.setup()
  render(<I18nProvider><ProfileForm playerId="p" displayName="דנה" send={send} serverError={null}/></I18nProvider>)
  await user.click(screen.getByRole('button',{name:'שמירת הפרופיל שלי'}))
  expect(screen.getByRole('alert')).toHaveTextContent('יש למלא את השדה עיר.')
  await user.type(screen.getByLabelText('עיר',{exact:true}),'תל אביב')
  await user.type(screen.getByLabelText('אוכל אהוב',{exact:true}),'Pizza')
  await user.type(screen.getByLabelText('תחביב',{exact:true}),'שחמט')
  await user.selectOptions(screen.getByLabelText('סגנון מוזיקה אהוב',{exact:true}),'Rock')
  await user.click(screen.getByLabelText('אפשר להשתמש בשדה עיר בשאלות'))
  await user.click(screen.getByRole('button',{name:'שמירת הפרופיל שלי'}))
  const fields=(send.mock.calls[0][1] as PlayerProfile).fields
  expect(fields).toContainEqual({field_key:'city',value:'תל אביב',allow_question_usage:false})
  expect(fields).toContainEqual({field_key:'favorite_music',value:'Rock',allow_question_usage:true})
  expect(fields).toContainEqual({field_key:'favorite_food',value:'Pizza',allow_question_usage:true})
})

test.each(['<script>alert(1)</script>','<img src=x onerror=alert(1)>',`O'Reilly "hi"`, 'עברית?! {name}', 'א'.repeat(120)].flatMap(unsafe => ['QUESTION_ACTIVE','QUESTION_RESULTS'].map(state => [unsafe,state] as const)))('question and result values render as text: %s (%s)', (unsafe,state) => {
  const content={text:unsafe,options:[{option_id:'a',text:unsafe},{option_id:'b',text:'Safe'}]}
  const current={...view,question:{...q,...content},results:{...ended,...content},room:{...room,state:state as 'QUESTION_ACTIVE'|'QUESTION_RESULTS'}}
  const {container}=render(<I18nProvider><PlayerGameView session={player} view={current} {...callbacks}/></I18nProvider>)
  expect(screen.getByRole('heading',{name:unsafe})).toBeVisible()
  expect(container.querySelector('script,img')).toBeNull()
  expect(container.textContent).toContain(unsafe)
})
