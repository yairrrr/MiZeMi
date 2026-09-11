import { test, expect, type Page } from '@playwright/test'
import type { ServerMessage, Question, QuestionEnded } from '../src/types'

test('host and three mobile players complete ten rounds, timeout and reconnects', async ({ browser, baseURL }) => {
  const contexts = await Promise.all(Array.from({ length: 4 }, (_, i) => browser.newContext({
    viewport: i === 0 ? { width: 1440, height: 1000 } : { width: 390, height: 844 },
    isMobile: i !== 0, hasTouch: i !== 0,
  })))
  const pages = await Promise.all(contexts.map((context) => context.newPage()))
  const [host, ...players] = pages
  const messages = new Map<Page, ServerMessage[]>()
  const errors: string[] = []
  for (const page of pages) {
    messages.set(page, [])
    page.on('pageerror', (error) => errors.push(error.message))
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
    await host.getByRole('button', { name: 'Create Room' }).click()
    const code = (await host.getByLabel(/Room code/).textContent())!.trim()
    const profiles = [
      ['Dana', 'Haifa', 'pizza', 'chess', 'Rock', '16', 'Up'],
      ['Omer', 'Tel Aviv', 'sushi', 'running', 'Pop', '17', 'Cars'],
      ['Noa', 'Haifa', 'pizza', 'guitar', 'Jazz', '18', 'Up'],
    ]
    // An early player can finish before later students arrive; only host start closes admission.
    for (const [i, page] of players.entries()) {
      await page.goto(`${baseURL}/?room=${code}`)
      await page.getByLabel('Display Name').fill(profiles[i][0])
      await page.getByRole('button', { name: 'Join Room' }).click()
      await expect(page.getByRole('heading', { name: 'Tell the group about you' })).toBeVisible()
      const [, city, food, hobby, music, age, movie] = profiles[i]
      await page.getByLabel('City', { exact: true }).fill(city)
      await page.getByLabel('Favorite food', { exact: true }).fill(food)
      await page.getByLabel('Hobby', { exact: true }).fill(hobby)
      await page.getByLabel('Favorite music style', { exact: true }).selectOption(music)
      await page.getByLabel('Age (optional)').fill(age)
      await page.getByLabel('Favorite movie (optional)').fill(movie)
      await page.getByLabel('Something interesting about me (optional)').fill('PRIVATE_MARKER_DO_NOT_SHARE')
      await expect(page.getByLabel('Use Something interesting about me in questions')).not.toBeChecked()
      await noOverflow(page)
      await page.getByRole('button', { name: 'Save my profile' }).click()
      await page.getByRole('button', { name: 'I’m ready' }).click()
      await expect(page.getByText('You’re ready!')).toBeVisible()
      await expect(host.getByRole('button', { name: 'Start game', exact: true })).toBeEnabled()
    }
    await expect(host.getByRole('list', { name: 'Players' }).getByRole('listitem')).toHaveCount(3)
    await host.getByRole('button', { name: 'Start game', exact: true }).click()
    const totals = [0, 0, 0]
    for (let round = 0; round < 10; round += 1) {
      await expect(host.getByText(`Question ${round + 1} of 10`, { exact: true })).toBeVisible()
      const q = latest<Question>(host, 'question.started')!
      expect(q.time_limit_seconds).toBe(20)
      expect(q).not.toHaveProperty('correct_option_id')
      // Check all active frames, not just question.started.
      for (const page of pages) {
        const active = messages.get(page)!.slice(messages.get(page)!.findLastIndex((m) => m.event === 'question.started'))
        expect(JSON.stringify(active)).not.toContain('correct_option_id')
      }
      const chosen: (string | null)[] = []
      for (const [i, page] of players.entries()) {
        await expect(page.getByText(`Question ${round + 1} of 10`, { exact: true })).toBeVisible()
        await noOverflow(page)
        if (round === 0 && i === 2) { chosen.push(null); continue }
        const index = i % q.options.length
        chosen.push(q.options[index].option_id)
        await page.getByRole('group', { name: 'Answers' }).getByRole('button').nth(index).click()
        if (round === 0 && i === 0) {
          await expect(page.getByText(/Answer locked in!/)).toBeVisible()
          await page.reload()
          await expect(page.getByText(/Answer locked in!/)).toBeVisible()
          await expect(page.getByRole('group', { name: 'Answers' }).getByRole('button').first()).toBeDisabled()
        }
      }
      // Round 1 must close by the authoritative 20-second timer.
      await expect(host.getByRole('button', { name: 'Show leaderboard' })).toBeVisible({ timeout: 25_000 })
      for (const [i, page] of players.entries()) {
        await expect(page.getByLabel('Answer distribution')).toBeVisible()
        const result = latest<QuestionEnded>(page, 'question.ended')!
        expect(result.text).toBe(q.text)
        expect(result.options).toEqual(q.options)
        expect(result.statistics.answered_count).toBe(round === 0 ? 2 : 3)
        expect(result.player_result!.option_id).toBe(chosen[i])
        const correct = chosen[i] === result.correct_option_id
        expect(result.player_result!.is_correct).toBe(correct)
        if (correct) expect(result.player_result!.points_awarded).toBeGreaterThanOrEqual(500)
        else expect(result.player_result!.points_awarded).toBe(0)
        totals[i] += result.player_result!.points_awarded
        expect(result.player_result!.total_score).toBe(totals[i])
      }
      if (round === 0) {
        await host.reload()
        await players[0].reload()
        await expect(host.getByLabel('Answer distribution')).toBeVisible()
        await expect(players[0].getByLabel('Answer distribution')).toBeVisible()
      }
      await host.getByRole('button', { name: 'Show leaderboard' }).click()
      await expect(host.getByRole('heading', { name: 'Leaderboard', exact: true })).toBeVisible()
      if (round === 0) {
        await host.reload()
        await players[0].reload()
        await expect(host.getByRole('list', { name: 'Leaderboard' }).getByRole('listitem')).toHaveCount(3)
        await expect(players[0].getByRole('list', { name: 'Leaderboard' }).getByRole('listitem')).toHaveCount(3)
      }
      await host.getByRole('button', { name: round === 9 ? 'Show final results' : 'Next question' }).click()
    }
    await expect(host.getByRole('heading', { name: 'Final leaderboard' })).toBeVisible()
    for (const [i, page] of players.entries()) {
      await expect(page.getByText(/You finished/)).toContainText(`${totals[i].toLocaleString('en-US')} points`)
    }
    await host.reload()
    await players[0].reload()
    await expect(host.getByRole('heading', { name: 'Final leaderboard' })).toBeVisible()
    await expect(players[0].getByText(/You finished/)).toBeVisible()
    for (const page of pages) {
      await noOverflow(page)
      expect(JSON.stringify(messages.get(page))).not.toMatch(/host_token|player_token|PRIVATE_MARKER_DO_NOT_SHARE|profile_fields/)
    }
    await host.screenshot({ path: 'test-results/host-final.png', fullPage: true })
    await players[0].screenshot({ path: 'test-results/player-final.png', fullPage: true })
    expect(errors).toEqual([])
  } finally {
    await Promise.all(contexts.map((context) => context.close()))
  }
})
