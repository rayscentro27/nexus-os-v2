import type { V2ViewData } from '../types/v2-models'
import { V2_ROUTE_CONTRACTS } from '../routeContracts'
import { currentLabelFor } from '../utils/navigate'

/** Design-neutral route boundary until product/UX approves final composition. */
export function RouteContractV2({ path, data }: { path: string; data: V2ViewData }) {
  const contract = V2_ROUTE_CONTRACTS[path]
  const label = currentLabelFor(path)
  const live = data.mode === 'live'
  const state = data.mode === 'loading' ? 'LOADING' : data.loadError ? 'ERROR' : live ? 'LIVE' : 'EMPTY_OR_DEMO'

  return (
    <section
      aria-labelledby="v2-route-contract-title"
      data-v2-contract-route={path}
      data-real-backend-connected={live ? 'YES' : 'NO'}
      data-v2-state={state}
      className="v2-fade-in"
    >
      <h1 id="v2-route-contract-title">{label}</h1>
      <p>{contract?.purpose || 'Client workspace route'}</p>
      <p>Backend connection: {live ? 'Live client-scoped data' : state === 'LOADING' ? 'Loading' : 'Not connected'}</p>
      {data.loadError && <p role="alert">This section is temporarily unavailable. Please try again.</p>}
      {!data.loadError && !live && state !== 'LOADING' && <p>This section is ready for approved data wiring.</p>}
    </section>
  )
}
