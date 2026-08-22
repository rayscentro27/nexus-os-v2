import { describe, expect, it } from 'vitest';
import fs from 'node:fs';

const read = (path: string) => fs.readFileSync(path, 'utf8');

describe('actual Hermes Workroom voice wiring', () => {
  const workroom = read('src/components/HermesWorkroom.jsx');
  const specialist = read('src/components/SpecialistWorkroom.jsx');
  const panel = read('src/components/HermesChatPanel.jsx');
  const voice = read('src/admin/VoicePushToTalk.jsx');
  const css = read('src/styles/nexus-operating-ui.css');

  it('proves the production render tree reaches HermesChatPanel', () => {
    expect(workroom).toMatch(/import SpecialistWorkroom from ['"]\.\/SpecialistWorkroom['"]/);
    expect(specialist).toMatch(/import HermesChatPanel from ['"]\.\/HermesChatPanel['"]/);
    expect(specialist).toMatch(/<HermesChatPanel\b/);
  });

  it('renders one microphone immediately before the existing Send control', () => {
    expect(panel).toMatch(/import VoicePushToTalk from ['"]\.\.\/admin\/VoicePushToTalk['"]/);
    expect(panel).toMatch(/<VoicePushToTalk disabled=\{loading\} onTranscript=\{\(text\) => send\(text\)\} \/>/);
    expect(panel.indexOf('<VoicePushToTalk')).toBeLessThan(panel.indexOf('className="primary"'));
    expect((panel.match(/<VoicePushToTalk\b/g) || []).length).toBe(1);
    expect(css).toMatch(/\.nxos-chat-compose\s*\{[^}]*display:flex/);
    expect(css).toMatch(/\.nxos-chat-compose \.nexus-voice-button/);
  });

  it('keeps voice transcripts on the typed send path and avoids duplicate sends while loading', () => {
    expect(panel).toMatch(/const send = useCallback/);
    expect(panel).toMatch(/if \(!clean \|\| loading\) return/);
    expect(panel).toMatch(/const userMsg = \{ id: `\$\{now\}-ray`, role: 'ray', text: clean \}/);
    expect(panel).toMatch(/setMessages\(current => \{/);
    expect(panel).toMatch(/onKeyDown=.*send\(\)/s);
    expect(voice).toMatch(/VITE_NEXUS_VOICE_ENDPOINT/);
    expect(voice).not.toMatch(/VITE_NEXUS_VOICE_TOKEN|NEXUS_VOICE_LOCAL_TOKEN/);
  });
});
