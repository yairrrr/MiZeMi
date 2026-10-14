import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useI18n } from '../../i18n/I18n'

// The server sends no progress while the AI writes the questions, so the
// percentage is an estimate: it eases toward 95% over the expected time and
// only reaches 100% once the first question has actually arrived.
const CEILING = 95
const FINISH_MS = 650
const EXIT_MS = 1350

export function expectedGenerationMs(questionCount: number): number {
  return Math.min(120_000, Math.max(25_000, 10_000 + questionCount * 10_000))
}

export function estimatedPercent(elapsedMs: number, expectedMs: number): number {
  // At the expected time this reads ~86%; it keeps creeping, never past 95.
  return CEILING * (1 - Math.exp((-2.3 * elapsedMs) / expectedMs))
}

const STEPS = [
  'Reading your profiles…',
  'Finding what you have in common…',
  'Writing the questions…',
  'Shuffling the answers…',
] as const

type Props = {
  questionCount: number
  /** True once the game has started; plays the 100% finish, then calls onExited. */
  done: boolean
  onExited: () => void
}

export function AiLoadingScreen({ questionCount, done, onExited }: Props) {
  const { t } = useI18n()
  const [percent, setPercent] = useState(0)
  const [leaving, setLeaving] = useState(false)
  const startedAt = useRef(performance.now())
  const shown = useRef(0)
  const exited = useRef(onExited)
  exited.current = onExited

  useEffect(() => {
    if (done) return
    const expected = expectedGenerationMs(questionCount)
    const id = window.setInterval(() => {
      shown.current = estimatedPercent(performance.now() - startedAt.current, expected)
      setPercent(shown.current)
    }, 120)
    return () => window.clearInterval(id)
  }, [done, questionCount])

  useEffect(() => {
    if (!done) return
    const from = shown.current
    const begin = performance.now()
    let frame = requestAnimationFrame(function tick() {
      const k = Math.min(1, (performance.now() - begin) / FINISH_MS)
      setPercent(from + (100 - from) * (1 - (1 - k) ** 3))
      if (k < 1) frame = requestAnimationFrame(tick)
    })
    const leave = window.setTimeout(() => setLeaving(true), FINISH_MS + 250)
    const exit = window.setTimeout(() => exited.current(), EXIT_MS)
    return () => {
      cancelAnimationFrame(frame)
      window.clearTimeout(leave)
      window.clearTimeout(exit)
    }
  }, [done])

  const value = Math.round(percent)
  const complete = value >= 100
  const step = STEPS[Math.min(STEPS.length - 1, Math.floor((percent / CEILING) * STEPS.length))]

  return createPortal(
    <div className={`ai-loader${complete ? ' is-complete' : ''}${leaving ? ' is-leaving' : ''}`}>
      <div
        className="ai-loader-dial"
        role="progressbar"
        aria-label={t('AI is crafting your questions…')}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
      >
        <span className="ai-loader-glow" aria-hidden="true" />
        <span className="ai-loader-ring" aria-hidden="true" />
        <svg className="ai-loader-progress" viewBox="0 0 100 100" aria-hidden="true">
          <defs>
            <linearGradient id="ai-loader-arc" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#ffc94d" />
              <stop offset="1" stopColor="#6a49dc" />
            </linearGradient>
          </defs>
          <circle className="ai-loader-track" cx="50" cy="50" r="42.5" />
          <circle
            className="ai-loader-arc"
            cx="50" cy="50" r="42.5"
            pathLength={100}
            strokeDasharray={`${percent} 100`}
          />
        </svg>
        <div className="ai-loader-face">
          <PeopleMark />
          <strong className="ai-loader-wordmark" dir="ltr">MiZeMi</strong>
          <span className="ai-loader-tagline" dir="ltr">WHO’S WHO · MADE FOR YOUR GROUP</span>
          <span className="ai-loader-percent" dir="ltr">{value}<small>%</small></span>
        </div>
      </div>
      <div className="ai-loader-copy" aria-live="polite">
        <p className="ai-loader-title">{t(complete ? 'Your questions are ready!' : 'AI is crafting your questions…')}</p>
        <p key={complete ? 'done' : step} className="ai-loader-step">
          {complete ? t('Get ready…') : t(step)}
        </p>
      </div>
    </div>,
    document.body,
  )
}

/** The logo's three figures, drawn as vectors so they stay sharp on any screen. */
function PeopleMark() {
  return (
    <svg className="ai-loader-people" viewBox="0 0 200 112" aria-hidden="true">
      <defs>
        <linearGradient id="ai-p-yellow" x1="0" y1="0" x2="0.6" y2="1">
          <stop offset="0" stopColor="#ffd978" />
          <stop offset="1" stopColor="#f6b733" />
        </linearGradient>
        <linearGradient id="ai-p-purple" x1="0.2" y1="0" x2="0.8" y2="1">
          <stop offset="0" stopColor="#9278f2" />
          <stop offset="1" stopColor="#5b3cd4" />
        </linearGradient>
        <linearGradient id="ai-p-lavender" x1="0.3" y1="0" x2="0.7" y2="1">
          <stop offset="0" stopColor="#d6c8ff" />
          <stop offset="1" stopColor="#a688f4" />
        </linearGradient>
      </defs>
      <g className="ai-loader-rays" strokeLinecap="round" strokeWidth="5" fill="none">
        <path className="ray ray-1" d="M40 52 L30 47" stroke="#ffc94d" />
        <path className="ray ray-2" d="M48 41 L41 33" stroke="#ffc94d" />
        <path className="ray ray-3" d="M86 18 L80 9" stroke="#7656e3" />
        <path className="ray ray-4" d="M100 14 V3" stroke="#7656e3" />
        <path className="ray ray-5" d="M114 18 L120 9" stroke="#7656e3" />
        <path className="ray ray-6" d="M152 41 L159 33" stroke="#b9a2f8" />
        <path className="ray ray-7" d="M160 52 L170 47" stroke="#b9a2f8" />
      </g>
      <g className="ai-loader-person person-left">
        <circle cx="63" cy="56" r="15" fill="url(#ai-p-yellow)" />
        <path d="M39 100 C39 83 49 75 63 75 C77 75 87 83 87 100 Q87 104 83 104 H43 Q39 104 39 100 Z" fill="url(#ai-p-yellow)" />
      </g>
      <g className="ai-loader-person person-right">
        <circle cx="137" cy="56" r="15" fill="url(#ai-p-lavender)" />
        <path d="M113 100 C113 83 123 75 137 75 C151 75 161 83 161 100 Q161 104 157 104 H117 Q113 104 113 100 Z" fill="url(#ai-p-lavender)" />
      </g>
      <g className="ai-loader-person person-center" stroke="#fffaf3" strokeWidth="5" paintOrder="stroke">
        <circle cx="100" cy="41" r="19" fill="url(#ai-p-purple)" />
        <path d="M70 102 C70 79 84 66 100 66 C116 66 130 79 130 102 Q130 108 124 108 H76 Q70 108 70 102 Z" fill="url(#ai-p-purple)" />
      </g>
    </svg>
  )
}
