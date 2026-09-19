import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import { entitiesByType, formatEntityList } from '../src/lib/organizationalEntities'

describe('Admin control plane and organizational taxonomy', () => {
  it('keeps departments separate from agents and capabilities', () => {
    expect(entitiesByType('DEPARTMENT').map(item => item.name)).toContain('Research')
    expect(entitiesByType('AGENT').map(item => item.name)).toContain('Alpha')
    expect(entitiesByType('CAPABILITY').map(item => item.name)).toContain('Last30Days')
    expect(formatEntityList('DEPARTMENT')).not.toContain('Alpha (')
  })

  it('retains the existing campaign approval and all real controls', () => {
    const source = fs.readFileSync('src/admin/LiveCompanyIntelligence.jsx', 'utf8')
    expect(source).toContain('appr_f1c900e26b494b71b576877b9019b891')
    for (const label of ['APPROVE', 'REJECT', 'REQUEST CHANGES', 'ASK NOVA']) expect(source).toContain(label)
    expect(fs.readFileSync('netlify/functions/company-cycle-decision.mjs', 'utf8')).toContain('RAY_DECISION_RECORDED')
  })
})
