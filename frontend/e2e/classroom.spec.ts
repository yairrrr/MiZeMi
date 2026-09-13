import { test, expect, type Page } from '@playwright/test'
import { translate, type MessageKey, type Values } from '../src/i18n/messages'
import type { ServerMessage, Question, QuestionEnded } from '../src/types'

for (const scenario of [{ language: 'en', count: 20, knowledge: false }, { language: 'he', count: 7, knowledge: false }, { language: 'he', count: 20, knowledge: true }] as const) {
const { language, count, knowledge } = scenario
const playerCount = knowledge ? 5 : 3
const prefix = knowledge ? 'knowledge-he' : language
const t = (key: MessageKey, values?: Values) => translate(language, key, values)
test(`${prefix}: host and ${playerCount} mobile players complete ${count} rounds with reconnects and visual QA`, async ({ browser, baseURL }) => {
  const contexts = await Promise.all(Array.from({ length: playerCount + 1 }, (_, i) => browser.newContext({
    viewport: i === 0 ? { width: 1440, height: 1000 } : { width: 390, height: 844 },
    isMobile: i !== 0, hasTouch: i !== 0,
  })))
  const pages = await Promise.all(contexts.map((context) => context.newPage()))
  const [host, ...players] = pages
  const messages = new Map<Page, ServerMessage[]>()
  const errors: string[] = []
  const externalRequests: string[] = []
  let semanticRounds = 0
  const explanations: string[] = []
  for (const page of pages) {
    messages.set(page, [])
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('request', (request) => {
      if (!['http://127.0.0.1:4173', 'http://127.0.0.1:8765'].includes(new URL(request.url()).origin)) externalRequests.push(request.url())
    })
    page.on('websocket', (ws) => ws.on('framereceived', ({ payload }) => {
      messages.get(page)!.push(JSON.parse(String(payload)))
    }))
  }
  const latest = <T>(page: Page, event: string): T | undefined =>
    messages.get(page)!.filter((m) => m.event === event).at(-1)?.payload as T | undefined
  const noOverflow = async (page: Page) => expect(await page.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth,
  )).toBe(true)

  try {
    await host.goto(baseURL!)
    await host.locator('#ui-language').selectOption(language)
    await expect(host.locator('html')).toHaveAttribute('dir', language === 'he' ? 'rtl' : 'ltr')
    await expect(host.getByRole('img', { name: 'MiZeMi' })).toBeVisible()
    await expect(host.locator('#question-count')).toHaveValue('20')
    expect(await host.getByRole('img', { name: 'MiZeMi' }).evaluate((img: HTMLImageElement) => img.naturalWidth === 1254 && img.naturalHeight === 1254)).toBe(true)
    await host.screenshot({ path: `test-results/${prefix}-home-desktop.png`, fullPage: true })
    await host.setViewportSize({ width: 390, height: 844 })
    await noOverflow(host)
    await host.screenshot({ path: `test-results/${prefix}-home-mobile.png`, fullPage: true })
    await host.setViewportSize({ width: 1440, height: 1000 })
    if (language === 'he') await host.locator('#question-count').fill(String(count))
    await host.getByRole('button', { name: t('Create Room') }).click()
    const code = (await host.locator('.room-code').textContent())!.trim()
    const profiles = knowledge ? [
      ['דנה', 'חיפה', 'פיצה', 'ריצה', 'Mizrahi', '20', 'המסור'],
      ['עומר', 'תל אביב', 'סושי', 'כדורגל', 'Mizrahi', '22', 'לזמן את הרוע'],
      ['נועה', 'רחובות', 'ספגטי', 'גלישה', 'Rock', '24', 'צעצוע של סיפור'],
      ['עמית', 'ראשון לציון', 'לזניה', 'גיטרה', 'Pop', '26', 'מוצאים את נמו'],
      ['ליאור', 'באר שבע', 'פלאפל', 'צילום', 'Jazz', '28', 'טיטניק (סרט, 1997)'],
    ] : language === 'he' ? [
      ['דנה', 'חיפה', 'פיצה', 'שחמט', 'Rock', '16', 'למעלה'],
      ['עומר', 'תל אביב', 'סושי', 'ריצה', 'Pop', '17', 'מכוניות'],
      ['נועה', 'חיפה', 'פיצה', 'גיטרה אקוסטית', 'Jazz', '18', 'למעלה'],
    ] : [
      ['Dana', 'Haifa', 'pizza', 'chess', 'Rock', '16', 'Up'],
      ['Omer', 'Tel Aviv', 'sushi', 'running', 'Pop', '17', 'Cars'],
      ['Noa', 'Haifa', 'pizza', 'guitar', 'Jazz', '18', 'Up'],
    ]
    // An early player can finish before later students arrive; only host start closes admission.
    for (const [i, page] of players.entries()) {
      await page.goto(`${baseURL}/?room=${code}`)
      await page.locator('#ui-language').selectOption(language)
      await expect(page.locator('html')).toHaveAttribute('dir', language === 'he' ? 'rtl' : 'ltr')
      await page.getByLabel(t('Display Name')).fill(profiles[i][0])
      await page.getByRole('button', { name: t('Join Room') }).click()
      await expect(page.getByRole('heading', { name: t('Tell the group about you') })).toBeVisible()
      const [, city, food, hobby, music, age, movie] = profiles[i]
      await page.getByLabel(t('City'), { exact: true }).fill(city)
      await page.getByLabel(t('Favorite food'), { exact: true }).fill(food)
      await page.getByLabel(t('Hobby'), { exact: true }).fill(hobby)
      await page.getByLabel(t('Favorite music style'), { exact: true }).selectOption(music)
      if (knowledge) {
        await page.getByLabel(t('Favorite artist') + t(' (optional)')).fill(['עומר אדם', 'עדן בן זקן', 'Taylor Swift', 'Metallica', 'Coldplay'][i])
        await page.getByLabel(t('Favorite song') + t(' (optional)')).fill(['Shake It Off - Taylor Swift', 'Blank Space', 'Enter Sandman', 'Yellow - Coldplay', 'Paradise - Coldplay'][i])
      }
      await page.getByLabel(t('Age') + t(' (optional)')).fill(age)
      await page.getByLabel(t('Favorite movie') + t(' (optional)')).fill(movie)
      await page.getByLabel(t('Something interesting about me') + t(' (optional)')).fill('PRIVATE_MARKER_DO_NOT_SHARE')
      await expect(page.getByLabel(t('Use {field} in questions', { field: t('Something interesting about me') }))).not.toBeChecked()
      await noOverflow(page)
      if (i === 0) await page.screenshot({ path: `test-results/${prefix}-profile.png`, fullPage: true })
      await page.getByRole('button', { name: t('Save my profile') }).click()
      await page.getByRole('button', { name: t('I’m ready') }).click()
      await expect(page.getByText(t('You’re ready!'))).toBeVisible()
      await expect(host.getByRole('button', { name: t('Start game'), exact: true })).toBeEnabled()
    }
    await expect(host.getByRole('list', { name: t('Players') }).getByRole('listitem')).toHaveCount(playerCount)
    await host.screenshot({ path: `test-results/${prefix}-lobby.png`, fullPage: true })
    await host.reload()
    await expect(host.getByText(t('{count} questions · {language}', { count, language: t(language === 'he' ? 'Hebrew' : 'English') }))).toBeVisible()
    await host.getByRole('button', { name: t('Start game'), exact: true }).click()
    const totals = Array<number>(playerCount).fill(0)
    for (let round = 0; round < count; round += 1) {
      await expect(host.getByText(t('Question {current} of {total}', { current: round + 1, total: count }), { exact: true })).toBeVisible()
      await noOverflow(host)
      expect(Number(await host.locator('.timer-seconds').textContent())).toBeLessThanOrEqual(20)
      const q = latest<Question>(host, 'question.started')!
      expect(q.time_limit_seconds).toBe(20)
      expect(q.language).toBe(language)
      expect(q.total_questions).toBe(count)
      expect(/[א-ת]/.test(q.text)).toBe(language === 'he')
      if (round === 0 || round === count - 1) await host.screenshot({ path: `test-results/${prefix}-question-${round}.png`, fullPage: true })
      expect(q).not.toHaveProperty('correct_option_id')
      expect(q).not.toHaveProperty('explanation')
      expect(q).not.toHaveProperty('knowledge_version')
      // Check all active frames, not just question.started.
      for (const page of pages) {
        const active = messages.get(page)!.slice(messages.get(page)!.findLastIndex((m) => m.event === 'question.started'))
        expect(JSON.stringify(active)).not.toContain('correct_option_id')
        expect(JSON.stringify(active)).not.toContain('explanation')
      }
      const chosen: (string | null)[] = []
      for (const [i, page] of players.entries()) {
        await expect(page.getByText(t('Question {current} of {total}', { current: round + 1, total: count }), { exact: true })).toBeVisible()
        await noOverflow(page)
        if (round === 0 || round === count - 1) await page.screenshot({ path: `test-results/${prefix}-player-${i}-question-${round}.png`, fullPage: true })
        if (language === 'en' && round === 0 && i === 2) { chosen.push(null); continue }
        const index = i % q.options.length
        chosen.push(q.options[index].option_id)
        await expect(page.getByRole('group', { name: t('Answers') }).getByRole('button').nth(index)).toBeEnabled()
        await page.getByRole('group', { name: t('Answers') }).getByRole('button').nth(index).click()
        if (round === 0 && i === 0) {
          await expect(page.getByText(t('Answer locked in!'), { exact: false })).toBeVisible()
          await page.reload()
          await expect(page.getByText(t('Answer locked in!'), { exact: false })).toBeVisible()
          await expect(page.getByRole('group', { name: t('Answers') }).getByRole('button').first()).toBeDisabled()
        }
      }
      // English round 1 closes by the authoritative 20-second timer.
      await expect(host.getByRole('button', { name: t('Show leaderboard') })).toBeVisible({ timeout: 25_000 })
      const hostResult = latest<QuestionEnded>(host, 'question.ended')!
      if (hostResult.explanation) {
        semanticRounds += 1
        explanations.push(hostResult.explanation)
        await expect(host.locator('.question-explanation')).toHaveText(hostResult.explanation)
        await expect(host.locator('.question-explanation')).toHaveAttribute('dir', language === 'he' ? 'rtl' : 'ltr')
      }
      for (const [i, page] of players.entries()) {
        await expect(page.getByLabel(t('Answer distribution'))).toBeVisible()
        const result = latest<QuestionEnded>(page, 'question.ended')!
        expect(result.text).toBe(q.text)
        expect(result.options).toEqual(q.options)
        expect(result.explanation).toBe(hostResult.explanation)
        if (result.explanation) await expect(page.locator('.question-explanation')).toHaveText(result.explanation)
        expect(result.statistics.answered_count).toBe(language === 'en' && round === 0 ? 2 : playerCount)
        expect(result.player_result!.option_id).toBe(chosen[i])
        const correct = chosen[i] === result.correct_option_id
        expect(result.player_result!.is_correct).toBe(correct)
        if (correct) expect(result.player_result!.points_awarded).toBeGreaterThanOrEqual(500)
        else expect(result.player_result!.points_awarded).toBe(0)
        totals[i] += result.player_result!.points_awarded
        expect(result.player_result!.total_score).toBe(totals[i])
      }
      if (round === 0) {
        await noOverflow(host)
        await noOverflow(players[0])
        await host.screenshot({ path: `test-results/${prefix}-results.png`, fullPage: true })
        await players[0].screenshot({ path: `test-results/${prefix}-player-results.png`, fullPage: true })
        await host.reload()
        await players[0].reload()
        await expect(host.getByLabel(t('Answer distribution'))).toBeVisible()
        await expect(players[0].getByLabel(t('Answer distribution'))).toBeVisible()
        if (hostResult.explanation) {
          await expect(host.locator('.question-explanation')).toHaveText(hostResult.explanation)
          await expect(players[0].locator('.question-explanation')).toHaveText(hostResult.explanation)
        }
      }
      await host.getByRole('button', { name: t('Show leaderboard') }).click()
      await expect(host.getByRole('heading', { name: t('Leaderboard'), exact: true })).toBeVisible()
      if (round === 0) await host.screenshot({ path: `test-results/${prefix}-leaderboard.png`, fullPage: true })
      if (round === 0) {
        await host.reload()
        await players[0].reload()
        await expect(host.getByRole('list', { name: t('Leaderboard') }).getByRole('listitem')).toHaveCount(playerCount)
        await expect(players[0].getByRole('list', { name: t('Leaderboard') }).getByRole('listitem')).toHaveCount(playerCount)
      }
      await host.getByRole('button', { name: t(round === count - 1 ? 'Show final results' : 'Next question') }).click()
    }
    await expect(host.getByRole('heading', { name: t('Final leaderboard') })).toBeVisible()
    for (const [i, page] of players.entries()) {
      await expect(page.locator('.your-place')).toContainText(t('{score} points', { score: totals[i].toLocaleString('en-US') }))
    }
    await host.reload()
    await players[0].reload()
    await expect(host.getByRole('heading', { name: t('Final leaderboard') })).toBeVisible()
    await expect(players[0].locator('.your-place')).toBeVisible()
    for (const page of pages) {
      await noOverflow(page)
      expect(JSON.stringify(messages.get(page))).not.toMatch(/host_token|player_token|PRIVATE_MARKER_DO_NOT_SHARE|profile_fields/)
    }
    await host.screenshot({ path: `test-results/${prefix}-host-final.png`, fullPage: true })
    await players[0].screenshot({ path: `test-results/${prefix}-player-final.png`, fullPage: true })
    expect(errors).toEqual([])
    expect(externalRequests).toEqual([])
    if (knowledge) {
      expect(semanticRounds).toBeGreaterThanOrEqual(10)
      expect(explanations.some((text) => text.includes('המסור') && text.includes('לזמן את הרוע'))).toBe(true)
      expect(explanations.some((text) => text.includes('ספורט') && text.includes('אימה'))).toBe(true)
    }
  } finally {
    await Promise.all(contexts.map((context) => context.close()))
  }
})

}
