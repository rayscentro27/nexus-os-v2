import { describe, it, expect } from 'vitest';
import fs from 'node:fs';

const srcIndex = () => fs.readFileSync('public/got-funding/index.html', 'utf8');
const srcBackup = () => fs.readFileSync('public/got-funding.html', 'utf8');
const distIndex = () => fs.readFileSync('dist/got-funding/index.html', 'utf8');
const distBackup = fs.existsSync('dist/got-funding.html') ? () => fs.readFileSync('dist/got-funding.html', 'utf8') : null;
const netlify = () => fs.readFileSync('netlify.toml', 'utf8');

describe('Got Funding full static page fix', () => {
  describe('Source files contain full teaser', () => {
    it('public/got-funding/index.html has full teaser content', () => {
      const s = srcIndex();
      expect(s).toContain('Got Funding?');
      expect(s).toContain('goclear-got-funding');
      expect(s).toContain('data-netlify="true"');
      expect(s).toContain('name="consent"');
      expect(s).toContain('does not guarantee');
    });

    it('public/got-funding/index.html is NOT a wrapper-only page', () => {
      const s = srcIndex();
      expect(s).not.toContain('Open the GoClear Got Funding teaser');
      expect(s).not.toMatch(/<meta http-equiv="refresh"/);
    });

    it('public/got-funding.html has full teaser content', () => {
      const s = srcBackup();
      expect(s).toContain('Got Funding?');
      expect(s).toContain('goclear-got-funding');
      expect(s).toContain('name="consent"');
      expect(s).toContain('does not guarantee');
    });

    it('public/got-funding.html is NOT a wrapper-only page', () => {
      const s = srcBackup();
      expect(s).not.toContain('Open the GoClear Got Funding teaser');
      expect(s).not.toMatch(/<meta http-equiv="refresh"/);
    });
  });

  describe('Build output contains full teaser', () => {
    it('dist/got-funding/index.html exists', () => {
      expect(fs.existsSync('dist/got-funding/index.html')).toBe(true);
    });

    it('dist/got-funding/index.html contains "Got Funding?"', () => {
      expect(distIndex()).toContain('Got Funding?');
    });

    it('dist/got-funding/index.html contains the form', () => {
      expect(distIndex()).toContain('goclear-got-funding');
    });

    it('dist/got-funding/index.html contains consent', () => {
      expect(distIndex()).toContain('name="consent"');
    });

    it('dist/got-funding/index.html contains disclaimer', () => {
      expect(distIndex()).toContain('does not guarantee');
    });

    it('dist/got-funding/index.html does NOT contain wrapper link', () => {
      expect(distIndex()).not.toContain('Open the GoClear Got Funding teaser');
    });

    if (distBackup) {
      it('dist/got-funding.html exists and has full teaser', () => {
        const s = distBackup();
        expect(s).toContain('Got Funding?');
        expect(s).toContain('goclear-got-funding');
        expect(s).not.toContain('Open the GoClear Got Funding teaser');
      });
    }
  });

  describe('Netlify form markup exists', () => {
    it('has Netlify form attributes', () => {
      const s = srcIndex();
      expect(s).toContain('method="POST"');
      expect(s).toContain('data-netlify="true"');
      expect(s).toContain('netlify-honeypot');
      expect(s).toContain('name="form-name"');
    });
  });

  describe('No guarantee language', () => {
    it('does not contain positive guarantee claims', () => {
      const s = srcIndex();
      expect(s).not.toMatch(/guaranteed approval/i);
      expect(s).not.toMatch(/guaranteed funding/i);
      expect(s).not.toMatch(/we guarantee/i);
    });
  });

  describe('No Supabase or email sends', () => {
    it('has no Supabase client usage', () => {
      const s = srcIndex();
      expect(s).not.toMatch(/supabase|createClient/i);
    });

    it('has no email-send code', () => {
      const s = srcIndex();
      expect(s).not.toMatch(/resend|sendgrid|nodemailer/i);
    });
  });

  describe('Netlify routing', () => {
    it('/got-funding/ routes to index.html before SPA fallback', () => {
      const n = netlify();
      const gfIndex = n.indexOf('from = "/got-funding"');
      const spaIndex = n.indexOf('from = "/*"');
      expect(gfIndex).toBeGreaterThan(-1);
      expect(gfIndex).toBeLessThan(spaIndex);
    });

    it('routes to /got-funding/index.html', () => {
      const n = netlify();
      expect(n).toContain('to = "/got-funding/index.html"');
    });
  });
});
