import type { AlphaMemoryEntry } from "./alphaTypes";

export class AlphaLocalMemory {
  private entries: AlphaMemoryEntry[] = [];

  write(entry: AlphaMemoryEntry): void {
    this.entries = [...this.entries, structuredClone(entry)];
  }

  list(): AlphaMemoryEntry[] {
    return structuredClone(this.entries);
  }

  clear(): void {
    this.entries = [];
  }
}
