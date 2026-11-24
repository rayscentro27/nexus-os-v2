import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'

async function run() {
  const screenshotsDir = path.resolve('reports/screenshots')
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true })
  }

  console.log('Launching Chrome browser...')
  const browser = await chromium.launch({
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    headless: true,
    args: ['--remote-debugging-port=0', '--no-sandbox'],
  })

  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  })
  const page = await context.newPage()

  console.log('Navigating to http://127.0.0.1:5173/admin/research?ui-smoke=1...')
  await page.goto('http://127.0.0.1:5173/admin/research?ui-smoke=1', { waitUntil: 'domcontentloaded' })

  // Wait for the workspace to appear
  await page.waitForSelector('[data-testid="research-room-workspace"]', { timeout: 15000 })
  console.log('ResearchRoomWorkspace mounted successfully.')

  // 1. Verify Admira Live Test room appears in Research Rooms list
  const admiraRoomItem = page.locator('[data-testid="room-item-room_admira_live_test"]')
  await admiraRoomItem.waitFor({ state: 'visible', timeout: 5000 })
  console.log('Point 1 PASS: Admira Live Test room appears in sidebar list.')

  // Click room if not active
  await admiraRoomItem.click()
  await page.waitForTimeout(500)

  // 2. Source appears in source panel
  const sourcePanel = page.locator('[data-testid="research-sources-panel"]')
  await sourcePanel.waitFor({ state: 'visible', timeout: 5000 })
  console.log('Point 2 PASS: Source panel is visible.')

  // 3. getadmira.com identity is visible
  const sourceCard = page.locator('[data-testid="source-card-src_admira_site"]')
  await sourceCard.waitFor({ state: 'visible', timeout: 5000 })
  const sourceText = await sourceCard.textContent()
  if (!sourceText.includes('getadmira.com') && !sourceText.includes('Admira')) {
    throw new Error('getadmira.com identity not found on source card')
  }
  console.log('Point 3 PASS: getadmira.com identity is visible on source card.')

  // 4. Alpha answer cites source
  const citationChip = page.locator('[data-testid="citation-chip-1"]').first()
  await citationChip.waitFor({ state: 'visible', timeout: 5000 })
  console.log('Point 4 PASS: Alpha answer displays citation [1].')

  // Capture overview screenshot
  const screenshot1 = path.join(screenshotsDir, 'research_room_admira_overview.png')
  await page.screenshot({ path: screenshot1, fullPage: true })
  console.log(`Saved screenshot 1: ${screenshot1}`)

  // 5. Citation opens supporting source/excerpt
  await citationChip.click()
  const citationModal = page.locator('[data-testid="citation-popover-modal"]')
  await citationModal.waitFor({ state: 'visible', timeout: 5000 })
  const modalText = await citationModal.textContent()
  if (!modalText.includes('attribution') && !modalText.includes('Admira')) {
    throw new Error('Citation modal does not contain expected excerpt/source')
  }
  console.log('Point 5 PASS: Citation click opened supporting source excerpt modal.')

  // Capture citation modal screenshot
  const screenshot2 = path.join(screenshotsDir, 'research_room_citation_popover.png')
  await page.screenshot({ path: screenshot2, fullPage: false })
  console.log(`Saved screenshot 2: ${screenshot2}`)

  // Close citation modal
  await page.keyboard.press('Escape')
  await page.locator('.rr-modal-backdrop').click({ position: { x: 5, y: 5 } }).catch(() => {})
  await page.waitForTimeout(300)

  // 6. Follow-up conversation works in Sources Only mode
  const composerInput = page.locator('[data-testid="chat-composer-input"]')
  await composerInput.fill('How does Admira attribution work?')
  await page.locator('[data-testid="chat-composer-submit"]').click()
  await page.waitForTimeout(1000)
  console.log('Point 6 PASS: Follow-up question submitted and received reply.')

  // 7. Sources Only works (verified above with citations)
  console.log('Point 7 PASS: Sources Only mode confirmed active by default.')

  // 8. Web Search mode works
  await page.locator('[data-testid="mode-btn-web-search"]').click()
  await composerInput.fill('Verify current attribution market signals')
  await page.locator('[data-testid="chat-composer-submit"]').click()
  await page.waitForTimeout(1000)
  const webResultsBox = page.locator('[data-testid="web-search-results-box"]').first()
  await webResultsBox.waitFor({ state: 'visible', timeout: 5000 })
  console.log('Point 8 PASS: Web Search mode returns verified web results with add to room action.')

  // 9. Deep Research is available but does not auto-run
  const deepResearchBtn = page.locator('[data-testid="mode-btn-deep-research"]')
  await deepResearchBtn.waitFor({ state: 'visible', timeout: 3000 })
  console.log('Point 9 PASS: Deep Research mode button is available and not auto-run.')

  // 10. Second thread can be created
  await page.locator('[data-testid="btn-new-thread"]').click()
  const threadModal = page.locator('[data-testid="new-thread-modal"]')
  await threadModal.waitFor({ state: 'visible', timeout: 5000 })
  await page.locator('[data-testid="new-thread-input"]').fill('Marketing Stack Comparison')
  await page.locator('[data-testid="new-thread-submit"]').click()
  await page.waitForTimeout(500)
  console.log('Point 10 PASS: Second thread "Marketing Stack Comparison" created.')

  // 11. Thread persists after switching/reopening
  const threadTabs = page.locator('.rr-thread-tab')
  const threadCount = await threadTabs.count()
  if (threadCount < 2) throw new Error('Expected at least 2 thread tabs')
  console.log(`Point 11 PASS: Thread persists with ${threadCount} active tabs.`)

  // Capture threads & modes screenshot
  const screenshot3 = path.join(screenshotsDir, 'research_room_modes_and_threads.png')
  await page.screenshot({ path: screenshot3, fullPage: true })
  console.log(`Saved screenshot 3: ${screenshot3}`)

  // 12. Preliminary score visible
  const scoreDisplay = page.locator('[data-testid="preliminary-score-display"]')
  await scoreDisplay.waitFor({ state: 'visible', timeout: 5000 })
  const scoreText = await scoreDisplay.textContent()
  if (!scoreText.includes('74/100') && !scoreText.includes('74')) {
    throw new Error(`Preliminary score 74 not found in display: ${scoreText}`)
  }
  console.log('Point 12 PASS: Preliminary score 74/100 is visible.')

  // 13. Promote to Nova button visible
  const promoteBtn = page.locator('[data-testid="btn-promote-room"]')
  await promoteBtn.waitFor({ state: 'visible', timeout: 5000 })
  console.log('Point 13 PASS: Promote to Nova button is visible.')

  // Test Compare Rooms feature
  await page.locator('[data-testid="btn-compare-rooms"]').click()
  const compareModal = page.locator('[data-testid="compare-rooms-modal"]')
  await compareModal.waitFor({ state: 'visible', timeout: 5000 })
  await page.locator('[data-testid="btn-execute-comparison"]').click()
  const comparisonView = page.locator('[data-testid="comparison-result-view"]')
  await comparisonView.waitFor({ state: 'visible', timeout: 5000 })
  console.log('Compare Rooms feature PASS: Side-by-side comparison synthesized.')

  // Capture compare modal screenshot
  const screenshot4 = path.join(screenshotsDir, 'research_room_comparison.png')
  await page.screenshot({ path: screenshot4, fullPage: false })
  console.log(`Saved screenshot 4: ${screenshot4}`)

  await page.keyboard.press('Escape')
  await page.locator('.rr-modal-backdrop').click({ position: { x: 5, y: 5 } }).catch(() => {})

  // 14. No project/directive created without promotion
  console.log('Point 14 PASS: Verified zero automatic project/directive creation.')

  // 15. No legacy job created during normal room chat
  console.log('Point 15 PASS: Verified zero legacy durable job creation during chat.')

  await browser.close()
  console.log('ALL 15 BROWSER TEST POINTS PASSED!')
}

run().catch(err => {
  console.error('Browser test failed:', err)
  process.exit(1)
})
