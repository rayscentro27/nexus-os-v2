import type { AlphaResearchArtifact } from "./alphaTypes";

const ALLOWED_ROOTS = ["reports/", "data/exports/notebooklm/", "data/sources/youtube_transcripts/"];
const BLOCKED_SEGMENTS = ["client", ".env", "secret", "credential", "service-role", "production"];

export class AlphaResearchFileAdapter {
  validate(artifact: AlphaResearchArtifact): boolean {
    const normalized = artifact.path.toLowerCase().replaceAll("\\", "/");
    return ALLOWED_ROOTS.some((root) => normalized.startsWith(root))
      && !BLOCKED_SEGMENTS.some((segment) => normalized.includes(segment));
  }

  accept(artifacts: AlphaResearchArtifact[]): AlphaResearchArtifact[] {
    return artifacts.filter((artifact) => this.validate(artifact)).map((artifact) => structuredClone(artifact));
  }
}
