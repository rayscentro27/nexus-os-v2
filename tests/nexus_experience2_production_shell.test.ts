import { describe, expect, it } from 'vitest';
import fs from 'node:fs';

const read = (path: string) => fs.readFileSync(path, 'utf8');
const shell = read('src/admin/NexusExperienceAdmin.jsx');
const conversation = read('src/components/NexusAgentConversation.jsx');
const dispatch = read('src/lib/nexusAgentDispatch.ts');
const composer = read('src/components/NexusUniversalComposer.jsx');

describe('Nexus Experience 2.0 production shell', () => {
  it('exposes exactly six conceptual primary destinations', () => {
    for (const label of ['Command', 'Work', 'Agents', 'Business', 'Studio', 'System']) expect(shell).toContain(`label: '${label}'`);
    expect(shell).not.toContain('Command Center');
    expect(shell).not.toContain('Hermes Workroom');
  });

  it('keeps agent brains and destinations separate', () => {
    expect(dispatch).toContain('sendThroughCanonicalHermes');
    expect(dispatch).toContain('NOVA_ENDPOINT');
    expect(dispatch).toContain('respondAsAlpha');
    expect(dispatch).not.toContain('runHermesConversation');
    expect(dispatch).toContain('conversation_id: conversationId');
  });

  it('uses per-conversation persistence and addressable routes', () => {
    expect(conversation).toContain('nexus-experience-chat:${agent}:${id}');
    expect(shell).toContain('/admin/agents/${agent}/chat/${target}');
    expect(conversation).toContain('+ New Chat');
    expect(conversation).toContain('Open in new tab');
  });

  it('uses session-scoped agent selection and the universal voice composer', () => {
    expect(shell).toContain('sessionStorage');
    expect(composer).toContain('VoicePushToTalk');
    expect(composer).toContain('Nexus / Hermes');
    expect(composer).toContain('Nova');
    expect(composer).toContain('Alpha');
    expect(composer).toContain('Review it, then press Send.');
  });
});
