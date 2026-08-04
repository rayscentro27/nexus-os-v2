import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();

describe('client-facing Clyde naming', () => {
  it('does not expose internal Hermes labels in the client portal advisor surfaces', () => {
    const portal = fs.readFileSync(path.join(root, 'src/pages/client/WorldClassClientPortal.jsx'), 'utf8');
    const shell = fs.readFileSync(path.join(root, 'src/components/client/ClientPortalShell.jsx'), 'utf8');
    const clientSource = `${portal}\n${shell}`;

    expect(clientSource).toContain('Ask Clyde');
    expect(clientSource).toContain('Clyde Funding Readiness Guide');
    expect(clientSource).toContain('Clyde Guidance');
    expect(clientSource).not.toContain('Ask Hermes');
    expect(clientSource).not.toContain('Hermes Funding Readiness Guide');
    expect(clientSource).not.toContain('Hermes will organize');
    expect(clientSource).not.toContain('Hermes and GoClear prepare');
  });
});
