import React from 'react'
import { ApprovedClientPortal } from '../../client-v2/approved/ApprovedClientPortal'

function DemoBanner() {
  return (
    <div style={{
      background: 'linear-gradient(135deg, #fef3c7, #fde68a)',
      borderBottom: '2px solid #f59e0b',
      padding: '10px 20px',
      textAlign: 'center',
      fontWeight: 600,
      fontSize: '0.9rem',
      color: '#92400e',
      position: 'sticky',
      top: 0,
      zIndex: 9999,
    }}>
      Preview Mode — Demo data only. Not connected to a live client record.
    </div>
  )
}

export default function ClientPreviewPage() {
  return (
    <>
      <DemoBanner />
      <ApprovedClientPortal live={false} />
    </>
  )
}
