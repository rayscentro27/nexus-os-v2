# Got Funding — Manual Browser Test Checklist

**Generated**: 2026-07-04

---

## Pre-Deploy Checklist

- [ ] Open https://goclearonline.cc/got-funding/
- [ ] Confirm top gold early-access announcement bar appears
- [ ] Confirm hero says "Got Funding?"
- [ ] Confirm subheadline says "Get funding-ready before you apply."
- [ ] Confirm emotional success/growth visual panel appears (skyline, arrow, glow)
- [ ] Confirm "Preparation today. Opportunities tomorrow." caption visible
- [ ] Confirm 4 benefit icons row appears below hero
- [ ] Confirm "What Could Funding Help You Do?" section with 7 cards
- [ ] Confirm "How GoClear Helps You Prepare" section with 7 white cards
- [ ] Confirm "Why Preparation Matters" split panel with road/sunrise visual
- [ ] Confirm 4 process steps visible (Review → Identify → Build → Access)
- [ ] Confirm "This Is For You If..." checklist with 6 items
- [ ] Confirm form section with "Get on the Funding Readiness Early Access List"
- [ ] Confirm form is readable on desktop
- [ ] Resize browser to mobile width — confirm form is usable
- [ ] Confirm footer with GoClear branding and compliance text
- [ ] Confirm trust badges (Secure & Private, Your Data Stays Yours, You're in Control)

## Form Submission Test

- [ ] Fill in Name: "Test User"
- [ ] Fill in Email: (use test email)
- [ ] Select Business Owner: "Yes"
- [ ] Select Interest: "Get funding-ready"
- [ ] Check consent checkbox
- [ ] Click "Join the funding-ready list"
- [ ] Confirm redirect to /got-funding/thanks.html
- [ ] Confirm thank-you page loads with confirmation message
- [ ] Confirm "Back to Got Funding" button works

## Netlify Forms Verification

- [ ] Go to https://app.netlify.com/sites/nexusv20/forms
- [ ] Confirm test submission appears
- [ ] Delete synthetic test entry

## QR Code Test

- [ ] Scan QR from phone 1 → confirms full page loads
- [ ] Scan QR from phone 2 → confirms full page loads
- [ ] QR target: https://goclearonline.cc/got-funding/

## Post-Deploy Notes

Document any issues found during testing here:
