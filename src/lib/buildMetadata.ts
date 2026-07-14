export const BUILD_METADATA={
  commit:import.meta.env.VITE_BUILD_COMMIT||'unversioned',
  branch:import.meta.env.VITE_BUILD_BRANCH||'unknown',
  timestamp:import.meta.env.VITE_BUILD_TIMESTAMP||'unknown',
  environment:import.meta.env.MODE||'unknown',
  schemaCompatibility:'research-to-clyde-v1',
}
