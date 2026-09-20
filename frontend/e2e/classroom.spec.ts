import { test, expect, type Page } from '@playwright/test'
import { execFileSync } from 'node:child_process'
import { readFileSync, writeFileSync } from 'node:fs'
import { translate, type MessageKey, type Values } from '../src/i18n/messages'
import type { ServerMessage, Question, QuestionEnded, ProfileField } from '../src/types'

const knowledgeFixture = JSON.parse(readFileSync(new URL('./fixtures/knowledge-room.json', import.meta.url), 'utf8')) as { profiles: string[][] }

for (const scenario of [{ language: 'en', count: 20, knowledge: false }, { language: 'he', count: 7, knowledge: false }, { language: 'he', count: 20, knowledge: true }] as const) {
const { language, count, knowledge } = scenario
const playerCount = knowledge ? 5 : 3
const prefix = knowledge ? 'knowledge-he' : language
const t = (key: MessageKey, values?: Values) => translate(language, key, values)
test(`${prefix}: host and ${playerCount} mobile players complete a ${count}-question game with reconnects and visual QA`, async ({ browser, baseURL }, testInfo) => {
  const contexts = await Promise.all(Array.from({ length: playerCount + 1 }, (_, i) => browser.newContext({
    viewport: i === 0 ? { width: 1440, height: 1000 } : { width: 390, height: 844 },
    isMobile: i !== 0, hasTouch: i !== 0,
  })))
  const pages = await Promise.all(contexts.map((context) => context.newPage()))
  const [host, ...players] = pages
  const messages = new Map<Page, ServerMessage[]>()
  const submissions = new Map<Page, ProfileField[]>()
  const errors: string[] = []
  const externalRequests: string[] = []
  const finalQuestions: Pick<QuestionEnded, 'question_id' | 'text' | 'options' | 'correct_option_id' | 'explanation'>[] = []
  for (const page of pages) {
    messages.set(page, [])
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('request', (request) => {
      if (!['http://127.0.0.1:4173', 'http://127.0.0.1:8765'].includes(new URL(request.url()).origin)) externalRequests.push(request.url())
    })
    page.on('websocket', (ws) => {
      ws.on('framereceived', ({ payload }) => messages.get(page)!.push(JSON.parse(String(payload))))
      ws.on('framesent', ({ payload }) => {
        const message = JSON.parse(String(payload))
        if (message.event === 'player.profile_submit') submissions.set(page, message.payload.fields)
      })
    })
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
    const profiles = knowledge ? knowledgeFixture.profiles : language === 'he' ? [
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
      const [, city, food, hobby, music, age, movie, artist, song] = profiles[i]
      await page.getByLabel(t('City'), { exact: true }).fill(city)
      await page.getByLabel(t('Favorite food'), { exact: true }).fill(food)
      await page.getByLabel(t('Hobby'), { exact: true }).fill(hobby)
      await page.getByLabel(t('Favorite music style'), { exact: true }).selectOption(music)
      if (knowledge) {
        await page.getByLabel(t('Favorite artist') + t(' (optional)')).fill(artist)
        await page.getByLabel(t('Favorite song') + t(' (optional)')).fill(song)
      }
      await page.getByLabel(t('Age') + t(' (optional)')).fill(age)
      await page.getByLabel(t('Favorite movie') + t(' (optional)')).fill(movie)
      await page.getByLabel(t('Something interesting about me') + t(' (optional)')).fill('PRIVATE_MARKER_DO_NOT_SHARE')
      await expect(page.getByLabel(t('Allow {field} to be used for game questions', { field: t('Something interesting about me') }))).not.toBeChecked()
      await noOverflow(page)
      if (i === 0) await page.screenshot({ path: `test-results/${prefix}-profile.png`, fullPage: true })
      await page.getByRole('button', { name: t('Save my profile') }).click()
      await page.getByRole('button', { name: t('I’m ready') }).click()
      await expect(page.getByText(t('You’re ready!'))).toBeVisible()
      if (knowledge) {
        // Input evidence stays in this synthetic test; raw profiles no longer persist.
        const keys = ['city', 'favorite_food', 'hobby', 'favorite_music', 'age', 'favorite_movie', 'favorite_artist', 'favorite_song']
        expect(submissions.get(page)).toEqual([
          ...keys.map((field_key, index) => ({ field_key, value: field_key === 'age' ? Number(profiles[i][index + 1]) : profiles[i][index + 1], allow_question_usage: true })),
          { field_key: 'personal_fact', value: 'PRIVATE_MARKER_DO_NOT_SHARE', allow_question_usage: false },
        ])
      }
      await expect(host.getByRole('button', { name: t('Start game'), exact: true })).toBeEnabled()
    }
    await expect(host.getByRole('list', { name: t('Players') }).getByRole('listitem')).toHaveCount(playerCount)
    await host.screenshot({ path: `test-results/${prefix}-lobby.png`, fullPage: true })
    await host.reload()
    await expect(host.getByText(t('{count} questions · {language}', { count, language: t(language === 'he' ? 'Hebrew' : 'English') }))).toBeVisible()
    await host.getByRole('button', { name: t('Start game'), exact: true }).click()
    // The engine returns fewer questions than requested rather than one an earlier question already answers.
    await expect.poll(() => latest<{ total_questions: number }>(host, 'game.started')?.total_questions ?? 0).toBeGreaterThan(0)
    const rounds = latest<{ total_questions: number }>(host, 'game.started')!.total_questions
    expect(rounds).toBeLessThanOrEqual(count)
    if (knowledge) expect(rounds).toBe(count)
    if (rounds < count) await expect(host.getByText(t('Only {actual} of {requested} questions could be made from the shared profiles.', { actual: rounds, requested: count }))).toBeVisible()
    const totals = Array<number>(playerCount).fill(0)
    for (let round = 0; round < rounds; round += 1) {
      await expect(host.getByText(t('Question {current} of {total}', { current: round + 1, total: rounds }), { exact: true })).toBeVisible()
      await noOverflow(host)
      expect(Number(await host.locator('.timer-seconds').textContent())).toBeLessThanOrEqual(20)
      const q = latest<Question>(host, 'question.started')!
      expect(q.time_limit_seconds).toBe(20)
      expect(q.language).toBe(language)
      expect(q.total_questions).toBe(rounds)
      expect(/[א-ת]/.test(q.text)).toBe(language === 'he')
      if (round === 0 || round === rounds - 1) await host.screenshot({ path: `test-results/${prefix}-question-${round}.png`, fullPage: true })
      expect(q).not.toHaveProperty('correct_option_id')
      expect(q).not.toHaveProperty('explanation')
      expect(q).not.toHaveProperty('knowledge_version')
      expect(q).not.toHaveProperty('source_rule_id')
      expect(q).not.toHaveProperty('question_family')
      expect(q).not.toHaveProperty('metadata')
      // Check all active frames, not just question.started.
      for (const page of pages) {
        const active = messages.get(page)!.slice(messages.get(page)!.findLastIndex((m) => m.event === 'question.started'))
        expect(JSON.stringify(active)).not.toContain('correct_option_id')
        expect(JSON.stringify(active)).not.toContain('explanation')
      }
      const chosen: (string | null)[] = []
      for (const [i, page] of players.entries()) {
        await expect(page.getByText(t('Question {current} of {total}', { current: round + 1, total: rounds }), { exact: true })).toBeVisible()
        await noOverflow(page)
        if (round === 0 || round === rounds - 1) await page.screenshot({ path: `test-results/${prefix}-player-${i}-question-${round}.png`, fullPage: true })
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
      const { question_id, text, options, correct_option_id, explanation } = hostResult
      finalQuestions.push({ question_id, text, options, correct_option_id, explanation })
      if (hostResult.explanation) {
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
      await host.getByRole('button', { name: t(round === rounds - 1 ? 'Show final results' : 'Next question') }).click()
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
      const publicEvidence = testInfo.outputPath('knowledge-public-results.json')
      writeFileSync(publicEvidence, JSON.stringify(finalQuestions, null, 2))
      await testInfo.attach('knowledge-public-results', { path: publicEvidence, contentType: 'application/json' })
      // Internal metadata stays in the test process. The offline oracle links
      // these exact browser frames to the finished local game, checks the
      // seeded trace and counts reviewed fixture facts independently of rules.
      // Persistence runs in a worker, so allow its final transaction to finish.
      let evidence = ''
      await expect(async () => {
        evidence = execFileSync('../.venv/bin/python', ['../backend/tests/classroom_knowledge.py'], {
          input: JSON.stringify(finalQuestions), encoding: 'utf8', timeout: 15_000,
        })
      }).toPass({ timeout: 10_000 })
      const internalEvidence = testInfo.outputPath('knowledge-final-quiz.json')
      writeFileSync(internalEvidence, evidence)
      await testInfo.attach('knowledge-final-quiz', { path: internalEvidence, contentType: 'application/json' })
      // Question variety: the oracle reports the reasoning patterns and repeated
      // ideas it found in the same finished game, so the players' quiz is held
      // to the variety targets without pinning any question's wording.
      const summary = JSON.parse(evidence) as { reasoning_families: number; repeated_signatures: number }
      expect(summary.reasoning_families).toBeGreaterThanOrEqual(6)
      expect(summary.repeated_signatures).toBe(0)
    }
  } finally {
    await Promise.all(contexts.map((context) => context.close()))
  }
})

}
