# Production notes

Technical details for maintaining ScarletCal. For setup, use [the deployment guide](deployment.md).

## Operational safeguards and limits

- API requests are capped at 200,000 bytes before JSON parsing, including bodies
  without Content-Length. Schedules remain capped at 30,000 characters.
- Responses disable caching and MIME sniffing; application pages use a same-origin
  Content Security Policy. Swagger/Redoc are exempt from CSP because of their CDN
  assets. Pages response headers are controlled by GitHub, not this Python app.
- `scarletcal-web` caps concurrent connections/tasks at 32 and disables Uvicorn
  access logs. It emits request IDs, route templates, status codes and durations.
  It does not log schedules, arbitrary paths, queries, IPs, or exception text.
- Unexpected errors return generic messages with a request ID. Operators can use
  that ID to correlate failures, then reproduce with a synthetic input locally.
- There is no database, saved schedule, analytics, or browser localStorage.
  Schedules go from the browser to Render over HTTPS; GitHub serves static assets.
  Hosting providers may retain connection metadata under their own policies.
- Rate limiting across clients, request-read timeouts, monitoring/alerts, and
  dependency pinning remain operational follow-ups. Concurrency/body limits are
  not a replacement for an edge rate limiter or protection against sustained abuse.
- Builds resolve dependencies within pyproject ranges; CI tests Python 3.12–3.14
  and verifies wheel assets outside the checkout. This is not a locked deployment.

## Release verification and remaining coverage

Local automated checks cover request limits, streaming bypass attempts, CORS,
private error/log handling, package assets, new terms, and the calendar pipeline.
The in-app browser was checked for sample generation (140 events), invalid-input
recovery, preserved styling and responsive layout. See `phase9-verification.md`.
Check the repository Actions tab for the latest CI result. Live Render/Pages
verification remains pending hosting setup.

Additional real WebReg captures still need user-provided examples; the new Friday
fixture is explicitly synthetic. Apple Calendar, Outlook, Firefox/Safari and a
screen-reader audit remain unverified. Do not infer that these checks passed.

## References

- [GitHub Pages hosting limitations](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Render FastAPI deployment](https://render.com/docs/deploy-fastapi)
- [Render Blueprint reference](https://render.com/docs/blueprint-spec)
- [Official Rutgers calendar](https://scheduling.rutgers.edu/academic-calendar/)
