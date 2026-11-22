# To do: production monitoring

Planned work; monitoring implementation is deferred.

Reuse the existing structured logs, request references, and stalled-video recovery.

- [ ] Track failed generation, rendering, AI draft, clip, and publishing jobs.
- [ ] Summarize recent API errors and background-task failures, retaining request
      and task references for troubleshooting.
- [ ] Check PostgreSQL, Redis, queue backlogs, and stalled work.
- [ ] Check private R2 availability and free disk space for local processing files.
- [ ] Provide protected operator health details without exposing credentials,
      private media, provider responses, or internal tracebacks.
- [ ] Configure external availability monitoring and operator alerts so API or
      worker downtime can be detected even when background jobs cannot run.
- [ ] Test dependency outages, failure reporting, recovery, and alert deduplication
      without calling paid providers or changing persistent media.
