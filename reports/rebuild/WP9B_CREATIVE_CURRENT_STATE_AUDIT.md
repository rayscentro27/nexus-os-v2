# WP9B Creative current-state audit

The existing Creative stack is substantial but fragmented. `creative/department.py`
already produces four evidence-linked territories, deterministic landing-page
desktop/mobile renders, channel draft records, and a bounded FFmpeg video. The
Creative Lab and Intelligence modules add six concept directions, similarity
scoring, feedback memory, and critic panels. `creative/studio.py` owns governed
brief/assets/receipts and blocks publication. `media_library.py` provides
proxy/master/thumbnail derivatives and a private Supabase adapter. The review
component reads the indexed library and writes authenticated review decisions.

| Capability | Current implementation | Engine | Location | Proven | Limitation | Action |
|---|---|---|---|---|---|---|
| Research/context | Alpha-derived commercial mission and Creative Intelligence | deterministic persisted records | control plane | YES | no dedicated swipe fetcher | normalized packet |
| Brand | partial GoClear context in Studio | governed deterministic brief | local/control | PARTIAL | unknown brand fields remain sparse | explicit BrandProfile contract |
| Territories | department + Lab/Intelligence | deterministic multi-direction generation | local | YES | schemas differ | normalized WP9B objects |
| Critique/revision | genericness gate, critic panel, v1/v2 landing | deterministic + human review | local | YES | no single structured schema | normalized critic/revision |
| Image | prompts/layout specs only | no configured image provider | UNKNOWN | NOT_PROVEN | no authorized route | honest NOT_CONFIGURED route |
| Video | FFmpeg screenshot render | system FFmpeg | local | YES internal | not generative/provider-backed | render-ready job contract |
| Remote worker | Modal adapter exists | Modal, optional | remote if configured | CONTRACT | no configured zero-cost worker | adapter retained |
| Storage | private-shaped local object store + Supabase adapter | local/Supabase | local or remote | local YES, remote conditional | Supabase credentials not used here | remote contract and review refs |
| Review | `/operator/creative` component + Netlify write function | Supabase/authenticated browser | remote review surface | implementation | visual session not rerun in WP9B | preserve existing surface |
| Growth/Finance | Studio and prior commercial package | governed records | control plane | YES bounded | no public validation authority | package handoff + receipt |

Root cause of shallow overnight output: `generate_overnight_creative_asset_queue.py`
only ranks an opportunity and emits draft queue ideas. It does not call the
Creative Department, Lab, render, critic, review, or Finance path.
