# Nexus Funding Readiness Positioning Audit

Date: 2026-07-14
Starting commit: `f4d0f8b701676fdcbb93d923e4716922da2196f1`

## Risky wording found

| Surface | Previous wording | Exposure | Replacement / decision |
|---|---|---|---|
| World-class client portal | Credit Repair Journey, Credit Repair Case Engine, negative items, items to challenge | Client-facing | Credit Profile Optimization, Profile Review Cases, funding-impact/report items, items to review |
| Client portal shell/journey | GoClear Credit Repair, Credit Repair Journey | Client-facing | Nexus Funding Readiness, Credit Profile Optimization |
| Clyde guidance | Improve and repair your Credit Profile; choose items to challenge | Client-facing | Understand funding-readiness impact; review report items and documentation options |
| Client resources | Credit Repair Support | Client-facing | Credit Report Review Tools |
| Admin workbench | Credit Specialist Workbench, Client Queue, Parser Preview, negative candidates | Admin-visible | Credit & Funding Readiness Review, Review Queue, Report Analysis, funding-impact items |
| Letter workflow | Generic letter generation framing | Client/admin-visible | Draft Letter Tool, documentation preparation, required GoClear/client approval, outcome disclaimer |
| Case engine default goal | Challenge negative items and pursue removal | Client-visible through case payload | Review funding-impact items and prepare documentation options when appropriate |

## Internal/technical names intentionally retained

Compatibility routes such as `/client/credit-repair-journey`, functions such as `loadCreditRepairJourney`, database fields such as `credit_repair`, and files such as `creditRepairCaseEngine.ts` remain. They are technical compatibility identifiers, not product claims; renaming them would add migration and integration risk without improving visible positioning. Legitimate letter language asking a bureau to investigate, correct, or remove inaccurate/unverifiable information also remains inside a client-reviewed draft.

## Safety conclusion

No parser, review flow, dispute-letter tool, Clyde capability, route, admin guard, or DocuPost approval gate was removed. No deletion, score, or funding outcome is promised.
