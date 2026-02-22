import { chromium } from 'playwright'

const FRONTEND_URL = process.env.FRONTEND_URL ?? 'http://localhost:4173'

async function main() {
  const browser = await chromium.launch()
  const page = await browser.newPage()

  await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded' })

  // Wait for register form
  await page.fill('input[placeholder="Display name"]', 'Docker QA')
  const email = `qa-${Math.random().toString(16).slice(2)}@example.com`
  await page.fill('input[placeholder="Email"]', email)
  await page.click('text=Register & Generate Password')
  await page.waitForSelector('text=Generated Password:')
  const password = await page.textContent('div:has-text("Generated Password") >> p.font-mono')
  if (!password) throw new Error('Password not generated')

  await page.fill('form:nth-of-type(2) input[placeholder="Email"]', email)
  await page.fill('form:nth-of-type(2) input[placeholder="Password"]', password.trim())
  await page.click('form:nth-of-type(2) button:has-text("Login")')

  await page.waitForSelector('text=Outcome Leaderboard', { timeout: 15000 })
  console.log('Dashboard loaded for', email)

  await browser.close()
}

main().catch((err) => {
  console.error(err)
  process.exitCode = 1
})
