import {describe,it,expect} from 'vitest'; import {buildOperationalMetrics} from '../src/hermes/nexus/nexusOperationalMetrics';
describe('metrics',()=>{it('records safe internal counts only',()=>expect(buildOperationalMetrics('2026-07-04T00:00:00Z')).toMatchObject({operationalCyclesRun:1,researchCyclesRun:1,realClientRecords:0,secretsStored:0}))});
