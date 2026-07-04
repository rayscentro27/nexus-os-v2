import { describe, it, expect } from 'vitest';
import fs from 'node:fs';

const srcIndex = () => fs.readFileSync('public/got-funding/index.html', 'utf8');
const srcBackup = () => fs.readFileSync('public/got-funding.html', 'utf8');
const distIndex = () => fs.readFileSync('dist/got-funding/index.html', 'utf8');
const distThanks = fs.existsSync('dist/got-funding/thanks.html') ? () => fs.readFileSync('dist/got-funding/thanks.html', 'utf8') : null;

describe('Got Funding premium landing page', () => {
  describe('File existence', () => {
    it('public/got-funding/index.html exists', () => expect(fs.existsSync('public/got-funding/index.html')).toBe(true));
    it('public/got-funding.html exists', () => expect(fs.existsSync('public/got-funding.html')).toBe(true));
    it('public/got-funding/thanks.html exists', () => expect(fs.existsSync('public/got-funding/thanks.html')).toBe(true));
    it('dist/got-funding/index.html exists', () => expect(fs.existsSync('dist/got-funding/index.html')).toBe(true));
    it('dist/got-funding.html exists', () => expect(fs.existsSync('dist/got-funding.html')).toBe(true));
    it('dist/got-funding/thanks.html exists', () => expect(distThanks !== null).toBe(true));
  });

  describe('Both landing files aligned', () => {
    it('index.html and got-funding.html have same core content', () => {
      const a = srcIndex(); const b = srcBackup();
      expect(a).toContain('Got Funding?');
      expect(b).toContain('Got Funding?');
      expect(a).toContain('Get funding-ready before you apply');
      expect(b).toContain('Get funding-ready before you apply');
    });
  });

  describe('Hero content', () => {
    it('contains "Got Funding?"', () => expect(srcIndex()).toContain('Got Funding?'));
    it('contains "Get funding-ready before you apply"', () => expect(srcIndex()).toContain('Get funding-ready before you apply'));
    it('contains "Most businesses do not fail because the idea was bad"', () => {
      const s = srcIndex();
      expect(s).toContain("don't fail because the idea was bad");
    });
    it('contains "run out of money"', () => expect(srcIndex()).toContain('run out of money'));
  });

  describe('What Could Funding Help section', () => {
    it('contains section title', () => expect(srcIndex()).toContain('What Could Funding Help'));
    it('contains "Start a New Business"', () => expect(srcIndex()).toContain('Start a New Business'));
    it('contains "Improve Cash Flow"', () => expect(srcIndex()).toContain('Improve Cash Flow'));
    it('contains "Build Business Credit"', () => expect(srcIndex()).toContain('Build Business Credit'));
  });

  describe('How GoClear Helps section', () => {
    it('contains section title', () => expect(srcIndex()).toContain('How GoClear Helps'));
    it('contains "Personal Credit Profile Review"', () => expect(srcIndex()).toContain('Personal Credit Profile Review'));
    it('contains "Credit Utilization Insights"', () => expect(srcIndex()).toContain('Credit Utilization Insights'));
    it('contains "Business Setup Readiness"', () => expect(srcIndex()).toContain('Business Setup Readiness'));
    it('contains "Funding Readiness Gaps"', () => expect(srcIndex()).toContain('Funding Readiness Gaps'));
  });

  describe('Why Preparation Matters', () => {
    it('contains section title', () => expect(srcIndex()).toContain('Why Preparation Matters'));
  });

  describe('This Is For You If', () => {
    it('contains section title', () => expect(srcIndex()).toContain('This Is For You'));
  });

  describe('Form and CTA', () => {
    it('form has Netlify attributes', () => {
      const s = srcIndex();
      expect(s).toContain('method="POST"');
      expect(s).toContain('data-netlify="true"');
      expect(s).toContain('netlify-honeypot');
    });
    it('form action is /got-funding/thanks.html', () => expect(srcIndex()).toContain('action="/got-funding/thanks.html"'));
    it('form has honeypot', () => expect(srcIndex()).toContain('bot-field'));
    it('form has consent checkbox', () => expect(srcIndex()).toContain('name="consent"'));
    it('CTA says "Join the funding-ready list"', () => expect(srcIndex()).toContain('Join the funding-ready list'));
  });

  describe('Thank-you page', () => {
    it('thank-you page exists', () => expect(fs.existsSync('public/got-funding/thanks.html')).toBe(true));
    it('contains confirmation text', () => {
      const s = fs.readFileSync('public/got-funding/thanks.html', 'utf8');
      expect(s).toContain("you're on the GoClear Funding Readiness early access list");
    });
    it('contains no-guarantee disclaimer', () => expect(fs.readFileSync('public/got-funding/thanks.html', 'utf8')).toContain('does not guarantee'));
    it('has back link to /got-funding/', () => expect(fs.readFileSync('public/got-funding/thanks.html', 'utf8')).toContain('href="/got-funding/"'));
  });

  describe('Compliance', () => {
    it('has no Supabase code', () => expect(srcIndex()).not.toMatch(/supabase|createClient/i));
    it('has no email-send code', () => expect(srcIndex()).not.toMatch(/resend|sendgrid|nodemailer/i));
    it('has no external hotlinked images', () => expect(srcIndex()).not.toMatch(/src="https?:\/\/[^"]*\.(png|jpg|jpeg|webp|gif)/i));
    it('no guarantee promise outside disclaimer', () => {
      const s = srcIndex();
      expect(s).not.toMatch(/we guarantee/i);
      expect(s).not.toMatch(/guaranteed approval/i);
    });
    it('page works without JavaScript (no script tags)', () => expect(srcIndex()).not.toMatch(/<script[ >]/i));
    it('mockup image not required', () => expect(srcIndex()).not.toContain('got-funding-approved-mockup'));
  });
});
