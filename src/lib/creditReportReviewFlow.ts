export function getCreditReportReviewEntryOptions(providerConfigured = false) {
  return [
    {
      id: 'upload_credit_report',
      title: 'Upload Credit Report',
      description: 'Upload your latest report so Clyde can review your best options.',
      route: '/client/credit-profile',
      enabled: true,
    },
    {
      id: 'connect_monitoring_resource',
      title: 'Connect Credit Monitoring Resource',
      description: providerConfigured
        ? 'Connect through a secure configured provider.'
        : 'Secure connection is coming soon. For now, upload a recent report or view recommended monitoring resources.',
      route: '/client/resources?category=credit-monitoring',
      enabled: providerConfigured,
    },
    {
      id: 'need_help_getting_report',
      title: 'I Need Help Getting My Report',
      description: 'Ask GoClear for help getting a current credit report.',
      route: '/client/request-review?topic=credit-report-help',
      enabled: true,
    },
    {
      id: 'manual_negative_item',
      title: 'Manually Add Negative Item',
      description: 'Use non-sensitive fields only. Account last four only.',
      route: '/client/credit-repair-journey?action=manual-negative-item',
      enabled: true,
    },
  ]
}

export function getPostReportClydeRecommendations(hasReport: boolean) {
  if (!hasReport) {
    return [
      'Upload a credit report',
      'View recommended monitoring resources',
      'Ask GoClear for report help',
      'Manually add a negative item',
      'Request GoClear review',
    ]
  }
  return [
    'Choose items to challenge',
    'Review utilization improvement options',
    'Upload missing evidence',
    'Review dispute letters',
    'Request GoClear review',
  ]
}
