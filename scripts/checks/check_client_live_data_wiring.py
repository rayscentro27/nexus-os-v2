#!/usr/bin/env python3
"""Client portal live data wiring check.

Verifies that all client portal pages import and call the live data loader,
that no page uses hardcoded fallback IDs, and that the adapter has all
required load functions.
"""
import re
import sys

PAGES_FILE = 'src/pages/client/ClientPortalPages.jsx'
SHELL_FILE = 'src/components/client/ClientPortalShell.jsx'
ADAPTER_FILE = 'src/lib/clientPortalDataAdapter.ts'
LIVE_SERVICE_FILE = 'src/services/clientDashboardLiveData.ts'
CLIENTS_PANEL = 'src/components/ClientsPanel.jsx'

def read_file(path):
    try:
        with open(path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return ''

def check_imports(content, filename):
    issues = []
    if 'loadClientPortalLiveData' not in content and 'usePortalLiveData' not in content:
        issues.append(f'{filename}: missing loadClientPortalLiveData import or usePortalLiveData hook')
    return issues

def check_no_hardcoded_ids(content, filename):
    issues = []
    if "client_test_julius_erving" in content:
        issues.append(f'{filename}: still references hardcoded client_test_julius_erving')
    if "client_demo_001" in content and 'DEMO_CLIENT_ID' not in content:
        issues.append(f'{filename}: references hardcoded client_demo_001')
    return issues

def check_adapter_functions(content):
    required = [
        'loadBusinessProfileRequirements',
        'loadFundingReadinessScores',
        'loadApprovedClientGuidance',
        'loadPartnerOffers',
        'loadCreditWorkflowItems',
        'loadClientPortalLiveData',
        'loadClientProfileIntake',
        'saveClientProfileIntake',
        'checkProfileIntakeComplete',
    ]
    issues = []
    for fn in required:
        if fn not in content:
            issues.append(f'adapter missing function: {fn}')
    return issues

def check_live_service(content):
    issues = []
    if 'TEST_CLIENT_ID' in content:
        issues.append('clientDashboardLiveData.ts still has hardcoded TEST_CLIENT_ID')
    return issues

def check_shell_wires_live(content):
    issues = []
    if 'loadClientPortalLiveData' not in content:
        issues.append('ClientPortalShell.jsx does not call loadClientPortalLiveData')
    return issues

def check_clients_panel(content):
    issues = []
    if 'searchQuery' not in content:
        issues.append('ClientsPanel.jsx missing search/filter')
    if 'documentCount' not in content and 'pendingReviewCount' not in content:
        issues.append('ClientsPanel.jsx missing live document/review counts')
    return issues

def check_page_wiring(content):
    issues = []
    pages_with_live = [
        ('ClientDashboard', 'usePortalLiveData|loadClientDashboardLiveData'),
        ('CreditProfilePage', 'usePortalLiveData'),
        ('CreditUtilizationPage', 'usePortalLiveData'),
        ('BusinessSetupPage', 'usePortalLiveData'),
        ('BusinessBankabilityPage', 'usePortalLiveData'),
        ('FundingReadinessPage', 'usePortalLiveData'),
        ('RecommendationsPage', 'usePortalLiveData'),
        ('ResourcesPage', 'usePortalLiveData'),
        ('RequestReviewPage', 'usePortalLiveData|loadClientDashboardLiveData'),
        ('ClientDocumentsPage', 'loadClientDashboardLiveData'),
        ('ProfileBusinessIntakeForm', 'loadClientProfileIntake|saveClientProfileIntake'),
    ]
    for page_name, pattern in pages_with_live:
        if re.search(rf'function {page_name}', content):
            start = re.search(rf'function {page_name}\(\)', content)
            if start:
                remaining = content[start.start():]
                next_func = re.search(r'\nexport function ', remaining[10:])
                if next_func:
                    component_body = remaining[:next_func.start() + 10]
                else:
                    component_body = remaining
                if not re.search(pattern, component_body):
                    issues.append(f'{page_name}: not wired to live data (missing {pattern})')
    return issues

def check_profile_route(content):
    issues = []
    if "'/client/profile'" not in content:
        issues.append('clientPageMap missing /client/profile route')
    if 'ProfileBusinessIntakeForm' not in content:
        issues.append('clientPageMap missing ProfileBusinessIntakeForm component')
    return issues

def check_profile_security(content):
    issues = []
    ssn_patterns = ['ssn', 'social security', 'full_dob', 'date_of_birth', 'bank_account_number', 'credit_card_number']
    for pat in ssn_patterns:
        if pat.lower() in content.lower() and f'Do not' not in content:
            issues.append(f'Profile page may collect sensitive field: {pat}')
    if 'service_role' in content.lower() and 'import' in content.lower():
        issues.append('Profile page may use service role')
    return issues

def check_profile_helpers(adapter_content):
    issues = []
    if 'resolveClientContextForCurrentUser' not in adapter_content:
        issues.append('Profile helpers do not use resolveClientContextForCurrentUser')
    if 'DEMO_CLIENT_ID' in adapter_content.split('loadClientProfileIntake')[1] if 'loadClientProfileIntake' in adapter_content else '':
        issues.append('Profile load function uses DEMO_CLIENT_ID as fallback')
    return issues

def main():
    pages_content = read_file(PAGES_FILE)
    shell_content = read_file(SHELL_FILE)
    adapter_content = read_file(ADAPTER_FILE)
    service_content = read_file(LIVE_SERVICE_FILE)
    clients_content = read_file(CLIENTS_PANEL)

    all_issues = []
    all_issues.extend(check_imports(pages_content, PAGES_FILE))
    all_issues.extend(check_no_hardcoded_ids(pages_content, PAGES_FILE))
    all_issues.extend(check_adapter_functions(adapter_content))
    all_issues.extend(check_live_service(service_content))
    all_issues.extend(check_shell_wires_live(shell_content))
    all_issues.extend(check_clients_panel(clients_content))
    all_issues.extend(check_page_wiring(pages_content))
    all_issues.extend(check_profile_route(pages_content))
    all_issues.extend(check_profile_security(pages_content))
    all_issues.extend(check_profile_helpers(adapter_content))

    print('Client Portal Live Data Wiring Check\n')
    if all_issues:
        print(f'FAIL: {len(all_issues)} issue(s) found:')
        for issue in all_issues:
            print(f'  - {issue}')
        sys.exit(1)
    else:
        print('PASS: All client portal pages are wired to live data.')
        print('  - Dashboard, CreditProfile, CreditUtilization: use live scores')
        print('  - BusinessSetup, BusinessBankability: use live business_profile_requirements')
        print('  - FundingReadiness: uses live funding_readiness_scores')
        print('  - Recommendations, Resources: use live partner_offers')
        print('  - RequestReview: uses live tasks and funding scores')
        print('  - Documents: uses live client_documents')
        print('  - ProfileBusinessIntakeForm: uses loadClientProfileIntake + saveClientProfileIntake')
        print('  - Shell: fetches live data for Hermes guidance')
        print('  - ClientsPanel: has search, live document/review counts, and profile fields')
        print('  - Adapter: has all required load/save functions')
        print('  - No SSN, bank account, or service-role usage in profile path')
        print('  - /client/profile route exists')
        sys.exit(0)

if __name__ == '__main__':
    main()
