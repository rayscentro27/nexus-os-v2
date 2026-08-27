# Nexus Machine Profile

Safe machine/runtime inventory; private identifiers excluded.

- Host: Mac Mini
- OS: {'name': 'Darwin', 'release': '21.6.0', 'version': '12.7.6', 'build': '21H1320'}
- Architecture: x86_64
- Storage free bytes: 710859100160

## Python
- /Users/raymonddavis/.local/bin/python3.11: 3.11.15 — SSL HEALTHY OpenSSL 3.5.5 27 Jan 2026
- /Library/Developer/CommandLineTools/usr/bin/python3: 3.9.6 — SSL HEALTHY LibreSSL 2.8.3
- /usr/local/opt/python@3.14/bin/python3.14: 3.14.5 — SSL HEALTHY OpenSSL 3.6.3 9 Jun 2026
- /usr/local/opt/python@3.14/bin/python3.14: 3.14.5 — SSL HEALTHY OpenSSL 3.6.3 9 Jun 2026

## Target decisions
- Live research: {'decision': 'LOCAL_COMPATIBLE', 'runtime': '/Users/raymonddavis/.local/bin/python3.11', 'reason': 'healthy SSL-capable interpreter selected from machine profile'}
- Voice/browser: {'decision': 'LOCAL_COMPATIBLE', 'runtime': '/Users/raymonddavis/.local/bin/python3.11', 'reason': 'no unmet machine requirement detected'}
