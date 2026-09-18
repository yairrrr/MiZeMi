import { test, expect, type Page, type Locator } from '@playwright/test'
import { createRequire } from 'node:module'
import type { AxeResults } from 'axe-core'
import { translate, type Language, type MessageKey } from '../src/i18n/messages'

const require = createRequire(import.meta.url)
async function audit(page: Page) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const results: AxeResults = await page.evaluate(async () => {
    const engine = (window as unknown as { axe: typeof import('axe-core') }).axe
    return engine.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice'] } })
  })
  expect(results.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => ({ target: n.target, summary: n.failureSummary })) }))).toEqual([])
}
async function tabTo(page: Page, target: Locator) {
  await expect(target).toBeVisible()
  for (let i = 0; i < 100; i++) {
    if (await target.evaluate(el => el === document.activeElement)) return
    await page.keyboard.press('Tab')
  }
  throw new Error(`Control was not keyboard reachable: ${await target.getAttribute('id')}`)
}
async function activate(page: Page, target: Locator) {
  await tabTo(page, target)
  expect(await target.evaluate(el => getComputedStyle(el).outlineStyle)).toBe('solid')
  await page.keyboard.press('Enter')
}
async function type(page: Page, target: Locator, value: string) {
  await tabTo(page, target)
  await page.keyboard.press('ControlOrMeta+A')
  await page.keyboard.type(value)
}
async function reflow(page: Page) {
  const overflow = await page.evaluate(() => ({ width: window.innerWidth, scroll: document.documentElement.scrollWidth,
    elements: [...document.querySelectorAll('body *')].filter(el => { const r = el.getBoundingClientRect(); return r.width > 1 && (r.right > window.innerWidth + 1 || r.left < -1) }).slice(0, 12).map(el => el.tagName + '.' + el.className) }))
  expect(overflow.scroll, JSON.stringify(overflow)).toBeLessThanOrEqual(overflow.width)
}

for (const language of ['en', 'he'] as Language[]) {
  const t = (key: MessageKey) => translate(language, key)
  test(`${language}: legal pages, keyboard navigation, narrow layout and reduced motion`, async ({ page }, info) => {
    const sockets: string[] = []
    const requests: string[] = []
    page.on('websocket', ws => sockets.push(ws.url()))
    page.on('request', req => requests.push(new URL(req.url()).origin))
    await page.setViewportSize({ width: 1280, height: 900 })
    await page.goto(`/privacy?lang=${language}`)
    await expect(page.locator('html')).toHaveAttribute('lang', language)
    await expect(page.locator('html')).toHaveAttribute('dir', language === 'he' ? 'rtl' : 'ltr')
    await expect(page.locator('#retention')).toContainText(language === 'he' ? '7 ימים' : '7 days')
    await page.keyboard.press('Tab')
    await expect(page.getByRole('link', { name: t('Skip to main content') })).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('main')).toBeFocused()
    await audit(page)
    await page.screenshot({ path: info.outputPath(`${language}-privacy-desktop.png`), fullPage: true })
    for (const [path, label] of [['terms', 'Terms'], ['accessibility', 'Accessibility'], ['privacy', 'Privacy']] as const) {
      await activate(page, page.locator('footer').getByRole('link', { name: t(label), exact: true }))
      await expect(page).toHaveURL(new RegExp(`/${path}\\?lang=${language}$`))
      await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
      await page.setViewportSize({ width: 320, height: 720 })
      await reflow(page)
      await audit(page)
      await page.screenshot({ path: info.outputPath(`${language}-${path}-mobile.png`), fullPage: true })
      await page.screenshot({ path: info.outputPath(`${language}-${path}-viewport.png`) })
      // Text enlargement, not a claim to have tested OS/native browser zoom.
      await page.addStyleTag({ content: 'html { font-size: 200% !important }' })
      await reflow(page)
    }
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto(`/?lang=${language}`)
    expect(await page.locator('.brand-logo').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
    await audit(page)
    expect(sockets).toEqual([])
    expect([...new Set(requests)].sort()).toEqual(['http://127.0.0.1:4173', 'http://127.0.0.1:8765'])
    expect(await page.context().cookies()).toEqual([])
  })

  test(`${language}: keyboard-only host and players through profile, ready, quiz, results and finish`, async ({ browser }, info) => {
    const contexts = await Promise.all(Array.from({ length: 4 }, () => browser.newContext({ viewport: { width: 320, height: 800 } })))
    const [host, ...players] = await Promise.all(contexts.map(c => c.newPage()))
    try {
      await host.goto(`/?lang=${language}`)
      await type(host, host.locator('#question-count'), '1')
      await activate(host, host.getByRole('button', { name: t('Create Room'), exact: true }))
      const code = (await host.locator('.room-code').textContent())!.trim()
      for (const [i, player] of players.entries()) {
        await player.goto(`/?room=${code}&lang=${language}`)
        await type(player, player.locator('#display-name'), `Keyboard ${i + 1}`)
        await activate(player, player.getByRole('button', { name: t('Join Room'), exact: true }))
        await expect(player.getByRole('heading', { name: t('Tell the group about you') })).toBeFocused()
        // Validation identifies and focuses its field without sending a profile.
        await activate(player, player.getByRole('button', { name: t('Save my profile'), exact: true }))
        await expect(player.locator('#profile-city')).toBeFocused()
        await expect(player.locator('#profile-city')).toHaveAttribute('aria-invalid', 'true')
        await expect(player.locator('#profile-city')).toHaveAttribute('aria-describedby', 'profile-city-error')
        await type(player, player.locator('#profile-city'), 'Haifa')
        await type(player, player.locator('#profile-favorite_food'), 'pizza')
        await type(player, player.locator('#profile-hobby'), 'chess')
        await tabTo(player, player.locator('#profile-favorite_music'))
        // Native select type-ahead keeps the journey keyboard-only on macOS and Linux.
        if (language === 'he') {
          // Playwright's named-key map has no Hebrew layout; send the native Unicode keystroke.
          const keyboard = await player.context().newCDPSession(player)
          await keyboard.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'פ', text: 'פ', code: 'KeyP' })
          await keyboard.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'פ', code: 'KeyP' })
          await keyboard.detach()
        } else await player.keyboard.press('p')
        await expect(player.locator('#profile-favorite_music')).toHaveValue('Pop')
        await player.keyboard.press('Tab')
        await reflow(player)
        if (i === 0) {
          await audit(player)
          const popupPromise = player.waitForEvent('popup')
          await activate(player, player.getByRole('link', { name: t('Read the full Privacy Policy'), exact: false }))
          const popup = await popupPromise
          await expect(popup.getByRole('heading', { level: 1 })).toBeVisible()
          expect(await popup.evaluate(() => window.opener)).toBeNull()
          expect(await popup.evaluate(() => sessionStorage.getItem('mizemi.session'))).toBeNull()
          await popup.close()
          await expect(player.locator('#profile-city')).toHaveValue('Haifa')
          await player.screenshot({ path: info.outputPath(`${language}-profile-mobile.png`), fullPage: true })
          await player.locator('.collection-notice').scrollIntoViewIfNeeded()
          await player.screenshot({ path: info.outputPath(`${language}-notice-viewport.png`) })
        }
        await activate(player, player.getByRole('button', { name: t('Save my profile'), exact: true }))
        await activate(player, player.getByRole('button', { name: t('I’m ready'), exact: true }))
        await expect(player.getByText(t('You’re ready!'))).toBeVisible()
      }
      await audit(host)
      await activate(host, host.getByRole('button', { name: t('Start game'), exact: true }))
      await expect(players[0].locator('.stage h2')).toBeFocused()
      await audit(players[0])
      for (const player of players) {
        await activate(player, player.getByRole('group', { name: t('Answers') }).getByRole('button').first())
      }
      await expect(host.getByRole('button', { name: t('Show leaderboard'), exact: true })).toBeVisible()
      await expect(players[0].locator('.stage h2')).toBeFocused()
      await audit(players[0])
      await reflow(players[0])
      await activate(host, host.getByRole('button', { name: t('Show leaderboard'), exact: true }))
      await audit(host)
      await activate(host, host.getByRole('button', { name: t('Show final results'), exact: true }))
      await expect(players[0].getByRole('heading', { name: t('Final leaderboard'), exact: true })).toBeFocused()
      await reflow(host)
      await audit(host)
      await audit(players[0])
      await players[0].screenshot({ path: info.outputPath(`${language}-final-mobile.png`), fullPage: true })
      await activate(players[0], players[0].getByRole('button', { name: t('Play again'), exact: true }))
      expect(await players[0].evaluate(() => sessionStorage.getItem('mizemi.session'))).toBeNull()
    } finally { await Promise.all(contexts.map(c => c.close())) }
  })
}

test('GitHub Pages has accessible controls and authoritative cross-origin legal links', async ({ page }, info) => {
  await page.goto('http://127.0.0.1:8770/')
  await audit(page)
  for (const path of ['privacy', 'terms', 'accessibility']) {
    const link = page.locator(`footer a[href="https://mizemi-frontend.onrender.com/${path}?lang=en"]`)
    await tabTo(page, link)
    expect(await link.evaluate(el => getComputedStyle(el).outlineStyle)).toBe('solid')
  }
  await page.setViewportSize({ width: 320, height: 720 })
  await reflow(page)
  await audit(page)
  await page.screenshot({ path: info.outputPath('pages-mobile.png'), fullPage: true })
  await page.addStyleTag({ content: 'html { font-size: 200% !important }' })
  await reflow(page)
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.reload()
  await audit(page)
})
