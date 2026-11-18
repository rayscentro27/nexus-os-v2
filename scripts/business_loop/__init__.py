"""Nexus End-to-End Business Loop R1.

One opportunity through Research -> Marketing -> (Creative, Commerce) ->
Distribution -> Metrics -> Analysis -> Next Action, with durable project state,
validated department handoffs, and automatic continuation. Nexus is the
authority; n8n may only trigger ``loop.py tick``. Approval-gated actions pause
only themselves; quality/provider/department failures never end the project.
"""
