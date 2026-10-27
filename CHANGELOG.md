# Changelog

## 0.1.0-rc.1 — Unreleased

Initial source release candidate; not a claim of a previous public release.

- Preserve Turkish match browsing, scores, recent form, rule-based analysis and live refresh.
- Replace machine-specific setup with Python 3.12/Node 24 instructions, environment examples, a local API proxy and locked dependencies.
- Add 17 offline backend tests, four proxy-configuration tests, three production-browser tests and Windows/Linux backend plus Linux frontend CI.
- Report provider rate limits, timeouts, transport failures and malformed responses correctly instead of returning a successful empty form response; preserve successful empty schedules.
- Correct homepage form field mapping and add readable form labels.
- Remove unverified remote photos/fonts and logo rendering; exclude captured reports and generated builds; add provider attribution.
- Use the Lucide package for the header globe and retain its separate upstream notice.
- Add MIT licensing for original code based on the owner's provenance declarations and reviewed platform terms; preserve third-party/data exclusions.

Known limits: optional history can degrade silently; analysis is heuristic, not validated forecasting; live-provider and complete accessibility checks remain outstanding. No native/container artifact is cleared by this source candidate.
