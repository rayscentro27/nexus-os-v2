#!/usr/bin/env python3
"""Client portal button/action smoke check.

Scans compiled client portal files for buttons without onClick, href, or disabled.
"""
import re
import sys

BUTTON_PATTERN = re.compile(r'<button[^>]*>(.*?)</button>', re.DOTALL)
ONCLICK_PATTERN = re.compile(r'onClick\s*[={]')
DISABLED_PATTERN = re.compile(r'disabled')
HREF_PATTERN = re.compile(r'href\s*=')
NAVIGATE_PATTERN = re.compile(r'navigate|onNavigate|window\.location|pushState|assign')
PLACEHOLDER_PATTERN = re.compile(r'Coming soon|TODO|FIXME|placeholder|not implemented', re.IGNORECASE)

FILES_TO_CHECK = [
    'src/pages/client/ClientPortalPages.jsx',
    'src/components/client/ClientPortalShell.jsx',
    'src/components/client/ClientPortalUI.jsx',
    'src/components/client/DocumentUploadZone.tsx',
]

def check_file(filepath):
    issues = []
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        return issues

    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if '<button' not in line.lower():
            continue
        # Find the full button element (may span multiple lines)
        start = i - 1
        button_text = line
        if '</button>' not in line:
            for j in range(i, min(i + 10, len(lines))):
                button_text += lines[j]
                if '</button>' in lines[j]:
                    break

        has_onclick = bool(ONCLICK_PATTERN.search(button_text))
        has_disabled = bool(DISABLED_PATTERN.search(button_text))
        has_href = bool(HREF_PATTERN.search(button_text))
        has_nav = bool(NAVIGATE_PATTERN.search(button_text))
        has_placeholder = bool(PLACEHOLDER_PATTERN.search(button_text))

        if not has_onclick and not has_disabled and not has_href and not has_nav:
            # Extract button label
            label_match = re.search(r'>(.*?)<', button_text)
            label = label_match.group(1).strip() if label_match else '(unknown)'
            if label and not label.startswith('{') and not label.startswith('<'):
                issues.append({
                    'file': filepath,
                    'line': start + 1,
                    'label': label[:60],
                    'reason': 'no onClick/href/disabled/navigate' + (' (has placeholder)' if has_placeholder else ''),
                })
    return issues

def main():
    total_issues = []
    for f in FILES_TO_CHECK:
        issues = check_file(f)
        total_issues.extend(issues)

    if total_issues:
        print(f'FAIL: {len(total_issues)} dead button(s) found:')
        for issue in total_issues:
            print(f'  {issue["file"]}:{issue["line"]} — "{issue["label"]}" — {issue["reason"]}')
        sys.exit(1)
    else:
        print('PASS: All client portal buttons have handlers, are disabled, or navigate.')
        sys.exit(0)

if __name__ == '__main__':
    main()
