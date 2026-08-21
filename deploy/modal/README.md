# Modal remote CPU deployment

`modal_app.py` is a thin deployment adapter around the existing
`nexus.remote-job.v1` worker. It exposes only authenticated `submit` and
`health` Web Functions, with one CPU container maximum and scale-to-zero.

Modal's `Image.from_dockerfile` uses the existing worker Dockerfile and then
clears its fixed local entrypoint for the Modal function runtime. Modal ignores
Dockerfile `USER` and runs containers as uid 0; application authority remains
bounded by the capability registry, HMAC validation, public-web policy, and
absence of Nexus secrets other than the dedicated worker HMAC.
