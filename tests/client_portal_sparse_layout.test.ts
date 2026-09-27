import { describe, expect, it } from 'vitest'
import fs from 'node:fs'

const dashboard = fs.readFileSync('src/client-v2/approved/components/views/DashboardView.tsx', 'utf8')

describe('GoClear sparse mission layout contract', () => {
  it('keeps four approved mission slots without inventing an actionable task', () => {
    expect(dashboard).toContain('const missionSlots: Array<Mission | null>')
    expect(dashboard).toContain('No current mission')
    expect(dashboard).toContain('Waiting for next action')
    expect(dashboard).toContain('No points or action available')
    expect(dashboard).not.toContain('completeMission(`mission-slot-')
  })

  it('does not truncate a live mission response larger than the approved shell', () => {
    expect(dashboard).toContain('missions.length >= 4')
    expect(dashboard).not.toContain('missions.slice(0, 4)')
  })
})
