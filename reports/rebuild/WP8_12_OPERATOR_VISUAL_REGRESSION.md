# WP8.12 Operator Visual Regression

Baseline files captured by the authenticated Playwright suite:

- `reports/rebuild/wp8_12_operator_home_desktop.png`
- `reports/rebuild/wp8_12_operator_home_mobile.png`
- `reports/rebuild/wp8_12_operator_creative_desktop.png`
- `reports/rebuild/wp8_12_operator_creative_mobile.png`

The suite re-renders these surfaces and checks responsive overflow. `OPERATOR_UI_REVISION=PASS` is satisfied by changing the duplicated Creative shell heading to the decision-oriented “Choose the next move” after screenshot critique, followed by authenticated desktop/mobile rerender. `OPERATOR_VISUAL_REGRESSION=PASS` is the focused screenshot contract for future changes.
