import { describe, it, expect } from 'vitest';
import fs from 'node:fs';

const srcIndex = () => fs.readFileSync('public/got-funding/index.html', 'utf8');
const srcBackup = () => fs.readFileSync('public/got-funding.html', 'utf8');
const distIndex = () => fs.readFileSync('dist/got-funding/index.html', 'utf8');
const distThanks = fs.existsSync('dist/got-funding/thanks.html') ? () => fs.readFileSync('dist/got-funding/thanks.html', 'utf8') : null;
const detectionSrc = () => fs.readFileSync('public/got-funding/netlify-form-detection.html', 'utf8');

describe('Got Funding premium landing page', () => {
  describe('File existence', () => {
    it('public/got-funding/index.html exists', () => expect(fs.existsSync('public/got-funding/index.html')).toBe(true));
    it('public/got-funding.html exists', () => expect(fs.existsSync('public/got-funding.html')).toBe(true));
    it('public/got-funding/thanks.html exists', () => expect(fs.existsSync('public/got-funding/thanks.html')).toBe(true));
    it('public/got-funding/thanks/index.html exists', () => expect(fs.existsSync('public/got-funding/thanks/index.html')).toBe(true));
    it('local hero and preparation images exist', () => {
      expect(fs.existsSync('public/got-funding/assets/hero-business-success.png')).toBe(true);
      expect(fs.existsSync('public/got-funding/assets/hero-business-success.png')).toBe(true);
      expect(fs.existsSync('public/got-funding/assets/preparation-road.png')).toBe(true);
    });
    it('dist/got-funding/index.html exists', () => expect(fs.existsSync('dist/got-funding/index.html')).toBe(true));
    it('dist/got-funding.html exists', () => expect(fs.existsSync('dist/got-funding.html')).toBe(true));
    it('dist/got-funding/thanks.html exists', () => expect(distThanks !== null).toBe(true));
  });

  describe('Both landing files aligned', () => {
    it('index.html and got-funding.html are identical', () => {
      const a = srcIndex(); const b = srcBackup();
      expect(a).toBe(b);
    });
  });

  describe('Hero content', () => {
    it('contains "Got Funding?"', () => expect(srcIndex()).toContain('Got Funding?'));
    it('contains "Get funding-ready before you apply"', () => expect(srcIndex()).toContain('Get funding-ready before you apply'));
    it('contains "Most businesses do not fail because the idea was bad"', () => {
      const s = srcIndex();
      expect(s).toContain('don’t fail because the idea was bad');
    });
    it('contains "run out of money"', () => expect(srcIndex()).toContain('run out of money'));
  });

  describe('What Could Funding Help section', () => {
    it('contains section title', () => expect(srcIndex()).toContain('What Could Funding Help'));
    it('contains "Start a New Business"', () => expect(srcIndex()).toContain('Start a New Business'));
    it('contains cash flow and business credit options', () => {
      expect(srcIndex()).toContain('Cash Flow');
      expect(srcIndex()).toContain('Business Credit');
    });
  });

  describe('How GoClear Helps section', () => {
    it('contains section title', () => expect(srcIndex()).toContain('How GoClear Helps'));
    it('contains "Personal Credit Profile Review"', () => expect(srcIndex()).toContain('Personal Credit Profile Review'));
    it('contains "Credit Utilization Insights"', () => expect(srcIndex()).toContain('Credit Utilization Insights'));
    it('contains "Business Setup Readiness"', () => expect(srcIndex()).toContain('Business Setup Readiness'));
    it('contains "Funding Readiness Gaps"', () => expect(srcIndex()).toContain('Funding Readiness Gaps'));
  });

  describe('One-screen image-backed design', () => {
    it('uses local hero and road assets', () => {
      expect(srcIndex()).toContain('./assets/hero-business-success.png');
      expect(srcIndex()).toContain('./assets/preparation-road.png');
    });
    it('uses Manrope and Inter', () => {
      expect(srcIndex()).toContain('Manrope');
      expect(srcIndex()).toContain('Inter');
    });
    it('uses 100dvh and desktop overflow hidden with mobile scrolling', () => {
      const s = srcIndex();
      expect(s).toContain('height:100dvh');
      expect(s).toContain('overflow:hidden');
      expect(s).toContain('html,body{overflow:auto}');
    });
  });

  describe('This Is For You If', () => {
    it('contains section title', () => expect(srcIndex()).toContain('This Is For <span class="gold">You If...'));
  });

  describe('Form and CTA', () => {
    it('form name is goclear-got-funding', () => expect(srcIndex()).toContain('name="goclear-got-funding"'));
    it('form method is POST', () => expect(srcIndex()).toContain('method="POST"'));
    it('form has data-netlify="true"', () => expect(srcIndex()).toContain('data-netlify="true"'));
    it('form has bare netlify attribute', () => expect(srcIndex()).toContain(' netlify netlify-honeypot="bot-field"'));
    it('form has netlify-honeypot bot-field', () => expect(srcIndex()).toContain('netlify-honeypot="bot-field"'));
    it('form action is /got-funding/thanks.html', () => expect(srcIndex()).toContain('action="/got-funding/thanks.html"'));
    it('hidden form-name input exists', () => expect(srcIndex()).toContain('name="form-name"'));
    it('honeypot field exists', () => expect(srcIndex()).toContain('name="bot-field"'));
    it('CTA says "Join the funding-ready list"', () => expect(srcIndex()).toContain('Join the funding-ready list'));
  });

  describe('JS submit fallback', () => {
    it('JS fallback exists in source', () => {
      const s = srcIndex();
      expect(s).toContain('querySelector(\'form[name="goclear-got-funding"]\')');
      expect(s).toContain('form.addEventListener("submit"');
      expect(s).toContain('event.preventDefault()');
    });
    it('JS fallback encodes data as x-www-form-urlencoded', () => expect(srcIndex()).toContain('"application/x-www-form-urlencoded"'));
    it('JS fallback posts to /', () => expect(srcIndex()).toContain('fetch("/"'));
    it('JS fallback redirects to /got-funding/thanks.html', () => expect(srcIndex()).toContain('window.location.href = "/got-funding/thanks.html"'));
    it('JS fallback sets form-name before submit', () => expect(srcIndex()).toContain('formData.set("form-name", "goclear-got-funding")'));
    it('JS fallback does not use Supabase', () => expect(srcIndex()).not.toMatch(/supabase|createClient/i));
    it('JS fallback does not use localStorage', () => expect(srcIndex()).not.toMatch(/localStorage\.setItem|localStorage\.getItem/i));
    it('JS fallback does not send email', () => expect(srcIndex()).not.toMatch(/resend|sendgrid|nodemailer/i));
  });

  describe('Netlify detection fallback file', () => {
    it('detection file exists', () => expect(fs.existsSync('public/got-funding/netlify-form-detection.html')).toBe(true));
    it('detection file has matching form name', () => expect(detectionSrc()).toContain('name="goclear-got-funding"'));
    it('detection file has matching field names', () => {
      const s = detectionSrc();
      expect(s).toContain('name="form-name"');
      expect(s).toContain('name="bot-field"');
      expect(s).toContain('name="name"');
      expect(s).toContain('name="email"');
      expect(s).toContain('name="business_owner"');
      expect(s).toContain('name="interest"');
      expect(s).toContain('name="consent"');
    });
  });

  describe('Thank-you page', () => {
    it('thank-you html exists', () => expect(fs.existsSync('public/got-funding/thanks.html')).toBe(true));
    it('thank-you index route exists', () => expect(fs.existsSync('public/got-funding/thanks/index.html')).toBe(true));
    it('contains confirmation text', () => {
      const s = fs.readFileSync('public/got-funding/thanks.html', 'utf8');
      expect(s).toContain('You’re on the GoClear Funding Readiness early access list');
    });
    it('contains no-guarantee disclaimer', () => expect(fs.readFileSync('public/got-funding/thanks.html', 'utf8')).toContain('does not guarantee'));
    it('has back link to /got-funding/', () => expect(fs.readFileSync('public/got-funding/thanks.html', 'utf8')).toContain('href="/got-funding/"'));
  });

  describe('Compliance', () => {
    it('has no Supabase code in source', () => expect(srcIndex()).not.toMatch(/supabase|createClient/i));
    it('has no email-send code in source', () => expect(srcIndex()).not.toMatch(/resend|sendgrid|nodemailer/i));
    it('has no guarantee promise outside disclaimer', () => {
      const s = srcIndex();
      expect(s).not.toMatch(/we guarantee/i);
      expect(s).not.toMatch(/guaranteed approval/i);
    });
    it('has no external hotlinked images', () => expect(srcIndex()).not.toMatch(/src="https?:\/\/[^"]*\.(png|jpg|jpeg|webp|gif)/i));
    it('mockup image not required', () => expect(srcIndex()).not.toContain('got-funding-approved-mockup'));
  });

  describe('Build output', () => {
    it('build output includes index', () => expect(fs.existsSync('dist/got-funding/index.html')).toBe(true));
    it('build output includes thank-you', () => expect(fs.existsSync('dist/got-funding/thanks.html')).toBe(true));
    it('build output includes thank-you index route', () => expect(fs.existsSync('dist/got-funding/thanks/index.html')).toBe(true));
  });
});
