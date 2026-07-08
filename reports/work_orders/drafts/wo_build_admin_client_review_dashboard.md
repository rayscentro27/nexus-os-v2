# Work Order: Build Admin Client Review Dashboard

**Status:** Draft
**Priority:** High
**Created:** 2026-07-07

## Goal
Create an admin-facing page to review client profiles, documents, and submissions.

## Why It Matters
Ray needs to review tester submissions, approve guidance, and track client progress.

## Scope
- New admin page under `/admin/clients` or similar
- List all clients with status
- View individual client profile, tasks, scores
- View uploaded documents
- Approve/reject guidance items
- Add admin notes

## Acceptance Criteria
- Admin can list all clients
- Admin can view individual client details
- Admin can see uploaded documents
- Admin can approve/reject items
- RLS allows admin access

## Files Involved
- `src/admin/NexusAdminUI.jsx` (add client review panel)
- `src/components/` (new client review components)

## Risk Level
Low — admin-only, uses existing RLS patterns

## Test Plan
1. Navigate to admin client list
2. Select a client
3. View profile, tasks, scores
4. Test approval workflow
