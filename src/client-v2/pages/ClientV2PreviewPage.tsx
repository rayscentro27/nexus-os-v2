import { ApprovedClientPortal } from '../approved/ApprovedClientPortal'

export function ClientV2PreviewPage() {
  return (
    <>
      <div className="v2-banner px-5 py-2.5 flex items-center justify-between gap-3">
        <span className="truncate">
          Design preview — V2 Clean-Room Client Portal. Demo data only; authenticated client data is never loaded in preview mode.
        </span>
        <a
          href="/client/preview"
          className="shrink-0 font-semibold text-[#8A6420] hover:text-[#5E4316] transition-colors"
        >
          Compare classic preview →
        </a>
      </div>
      <ApprovedClientPortal live={false} />
    </>
  )
}
