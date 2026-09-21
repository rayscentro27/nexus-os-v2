# Nexus Web Deployment Standard V1

## Canonical policy

```text
PRIMARY_DEPLOYMENT_METHOD=GIT_CONNECTED_CLOUD_DEPLOY
PROVIDER=NETLIFY
TRIGGER=GIT_PUSH_OR_MERGE
BUILD_LOCATION=CLOUD
PRODUCTION_BRANCH=main
PUBLISH_DIRECTORY=dist
```

The release path is:

```text
source change → focused local validation → commit → push → cloud build →
cloud deploy → deployment receipt → public commit verification → browser QA
```

The Mac mini may run development, focused tests, typechecks, and optional
local validation builds. It is not the normal production deployment engine.

## Provider boundary

Marketing, Creative, and client-facing feature work do not call Netlify. They
request the Systems capability `systems.web_deploy`, which owns repository,
branch, commit, provider, build, deploy, receipt, rollback, and browser
verification state.

## Direct Netlify CLI policy

```text
NETLIFY_CLI_DEFAULT_ALLOWED=NO
NEXUS_ALLOW_LEGACY_NETLIFY_CLI_DEPLOY=NO
```

Direct `netlify deploy` paths are legacy/emergency-only. The guard requires an
explicit `NEXUS_ALLOW_LEGACY_NETLIFY_CLI_DEPLOY=YES`, a non-empty reason, and a
receipt path. Without all three, the request is rejected before provider
execution. This exception does not change the canonical Git-connected path.

## Build metadata

Cloud builds must inject `VITE_BUILD_COMMIT`, `VITE_BUILD_BRANCH`, and
`VITE_BUILD_TIMESTAMP`. The application exposes the safe build metadata through
`window.__NEXUS_BUILD_METADATA__`; release verification must compare the public
marker with the pushed commit.

## Preview workflow

```text
feature/fix branch → push → cloud preview → browser/mobile QA → repair →
push updated branch → preview re-test → merge → production deploy
```

Production is not the iterative scratch environment.

