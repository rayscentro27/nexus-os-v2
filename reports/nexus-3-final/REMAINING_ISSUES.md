# Remaining Issues

| Severity | Issue | Customer Impact | Security Impact | Action | Required Before Controlled Client Testing | Required Before Live Launch |
|---|---|---|---|---|---|---|
| low | Vite main bundle remains above 500 kB warning threshold. | Slower first load on weak networks. | none known | Add route-level lazy loading for admin/client heavy workspaces. | no | no |
| low | Full axe scan was not run because axe dependency is not installed. | Minor accessibility defects may remain undetected. | none known | Add `@axe-core/playwright` and run primary-route axe suite. | no | recommended |
| low | Admin shell still contains some Nexus OS v2 labels and dark console styling. | Admin polish inconsistency only; workflow is functional. | none known | Admin visual polish sprint. | no | no |
| medium | Python shared recommendation test could not run because `pytest` is not installed locally. | No runtime customer impact observed. | none known | Install pytest or convert that test to Vitest/Node harness. | no | recommended |

No blocker remains for controlled client testing.
