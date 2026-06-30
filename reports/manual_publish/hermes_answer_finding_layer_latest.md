# Hermes Answer Finding Layer Report

Generated: 2026-06-29

## Summary
Hermes can now search Nexus context to find answers from reports, research, offers, revenue, and blockers.

## Search Capabilities
- **Report Search**: Scans reports/runtime/*.json and reports/manual_publish/*.json
- **Research Registry**: Scans data/research/*.json and reports/runtime/research_*.json
- **Offer Registry**: Scans data/offers/*.json and data/offer_registry/*.json
- **Revenue Dashboard**: Scans data/revenue/*.json and reports/runtime/revenue_*.json
- **Blocker Matrix**: Scans data/blockers/*.json and reports/runtime/blocker_*.json

## Search Algorithm
- Word frequency scoring
- Minimum word length: 3 characters
- Preview length: 120 characters
- Confidence threshold: 0.6
- Max matches returned: 20

## Context Integration
- **JS Engine**: nexusTopics knowledge base embedded in hermesWorkroomData.js
- **Python Scripts**: search_hermes_context.py and related scripts
- **Message Handler**: handle_hermes_message.py loads context and searches before responding

## Test Results
- 6 test messages run
- Intents classified: greeting, nexus_topic, opinion, money, blockers, summary
- Context search triggered for all applicable messages
- Suggested answers generated from search results

## Files Created
- scripts/hermes/search_hermes_context.py
- scripts/hermes/search_nexus_reports.py
- scripts/hermes/search_research_registry.py
- scripts/hermes/search_business_context.py
- scripts/hermes/load_hermes_context.py
