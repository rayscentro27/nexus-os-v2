import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const ROOT = process.cwd()
const portalSource = readFileSync(resolve(ROOT, 'src/pages/client/WorldClassClientPortal.jsx'), 'utf8')

describe('Nexus 3.0 route replacement', () => {
  it('renders the active route panel directly instead of stacking legacy client journey chrome', () => {
    expect(portalSource).toContain('<div className="wc-pageHost">{panel}</div>')
    expect(portalSource).not.toContain('<FundingReadinessHeader journey={journey}')
    expect(portalSource).not.toContain('<ClientRevenueServiceCard navigate={routeTo}')
    expect(portalSource).not.toContain('<GuidedClientJourneySurface')
  })

  it('keeps Credit and Business workspaces as tabs-first Nexus 3.0 route owners', () => {
    expect(portalSource).toContain('wc-panel wc-panel-credit"><SectionTabs tabs={creditTabs}')
    expect(portalSource).toContain('wc-panel wc-panel-business"><SectionTabs tabs={businessTabs}')
    expect(portalSource).toContain('wc-panel wc-panel-repair"><SectionTabs tabs={creditTabs}')
  })

  it('uses a dedicated Recommendations panel instead of reusing Resources', () => {
    expect(portalSource).toContain('function RecommendationsPanel')
    expect(portalSource).toContain('recommendations: <RecommendationsPanel')
    expect(portalSource).not.toContain('recommendations: <ResourcesPanel')
  })
})
