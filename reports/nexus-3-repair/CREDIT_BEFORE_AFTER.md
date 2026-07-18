# Credit Before / After

## Before

`/client/credit-profile` rendered:

- `FundingReadinessHeader`
- `ClientRevenueServiceCard`
- `GuidedClientJourneySurface routeKey="credit"`
- `CreditPanel`

This caused the approved Credit design to appear after legacy readiness and purchased-service content.

## After

`/client/credit-profile` renders:

- shared sidebar/topbar once;
- `CreditPanel` as the only center-column route panel;
- one Credit tab system;
- one approved Credit hero;
- one Hermes advisor panel.

## Local Browser Evidence

Local production preview at `127.0.0.1:4177`:

- `.wc-pageHost` direct children: `wc-panel wc-panel-credit`
- `Purchased service`: absent
- `Credit stage guidance`: absent
- direct guided stacks: `0`
- direct revenue cards: `0`
- Nexus 3.0 heroes: `1`
- Nexus 3.0 tab systems: `1`
- horizontal overflow: `false`
