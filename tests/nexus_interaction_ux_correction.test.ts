import { describe, expect, it } from 'vitest';
import fs from 'node:fs';

const read = (path: string) => fs.readFileSync(path, 'utf8');
const shell = read('src/admin/NexusExperienceAdmin.jsx');
const conversation = read('src/components/NexusAgentConversation.jsx');
const css = read('src/admin/nexusExperience2.css');

describe('Nexus interaction UX correction', () => {
  it('provides a persistent, searchable, agent-filtered thread rail', () => {
    expect(conversation).toContain('data-testid="nx2-thread-rail"');
    expect(conversation).toContain('Search chats');
    expect(conversation).toContain('All Chats');
    expect(conversation).toContain('Previous 7 days');
    expect(conversation).toContain('Archive');
    expect(conversation).toContain('onConversationChange?.(item.id, item.agent)');
  });

  it('keeps the message log and composer inside the application viewport', () => {
    expect(conversation).toContain('data-testid="nx2-conversation-log"');
    expect(conversation).toContain('data-testid="nx2-composer"');
    expect(css).toContain('height:calc(100dvh - 150px)');
    expect(css).toContain('.nx2-conversation-log{flex:1 1 auto;min-height:0');
    expect(css).toContain('.nx2-composer-wrap{flex:0 0 auto;position:sticky');
  });

  it('defines explicit breadcrumbs, parent Back actions, and contextual tabs', () => {
    expect(shell).toContain('data-testid="nx2-breadcrumb"');
    expect(shell).toContain('data-testid="nx2-back"');
    expect(shell).toContain('data-testid="nx2-secondary-nav"');
    expect(shell).toContain('studio-research');
    expect(shell).toContain('business-clients');
    expect(shell).toContain('system-mission-control');
    expect(shell).toContain('setSubpage(next.subpage || null)');
  });

  it('exposes Ask Nexus from non-agent areas with removable context', () => {
    expect(shell).toContain('data-testid="nx2-global-ask"');
    expect(shell).toContain('Ask Nexus');
    expect(shell).toContain('function globalContext()');
    expect(shell).toContain('onConversationChange={(id, next) => { if (next) { setSelectedAgent(next); setStoredAgent(next) } }}');
  });
});
