export const schedulerSummary = {
  installed: true,
  type: 'launchd',
  agents: [
    { name: 'com.nexus.daily-operating', time: '08:00 daily', lastStatus: '25/25 jobs passed' },
    { name: 'com.nexus.evening-closeout', time: '18:00 daily', lastStatus: '6/6 jobs passed' },
  ],
  schedulesRegistered: 53,
  safeJobsPassed: 18,
  approvalGatedJobs: 7,
  blockedJobs: 6,
  safeToLeaveRunning: true,
  manualRun: 'python3 scripts/activation/run_daily_operating_cycle.py --json',
  uninstall: 'python3 scripts/activation/uninstall_safe_internal_scheduler.py --json',
};
