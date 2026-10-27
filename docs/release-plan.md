# Initial release plan

Candidate: `0.1.0-rc.1` (proposed Git tag `v0.1.0-rc.1`). Pre-1.0 reflects the small offline-tested contract set and remaining live-provider/accessibility checks. The inherited package `1.0.0` was not evidence of a published release. See [changelog](../CHANGELOG.md).

## Completed maintenance and CI

The owner supplied provenance declarations; the published platform terms and prior file audit support original-code MIT preparation with residual risks recorded in [rights and assets](rights-and-assets.md). Third-party notices and provider-data exclusions remain separate. [PR #1](https://github.com/doksanbes/mac-analiz/pull/1) merged the source candidate into `main` with commit `e2400c5d2fcfc45bf6e2d7ec32c350a76c8cbfd3`. Its [post-merge CI run](https://github.com/doksanbes/mac-analiz/actions/runs/40546110561) passed all three jobs. This is not a tag, release or deployment.

## Publication gates

1. Source publication, PR #1 review and merge approvals are complete. New maintenance PRs must be reviewed at their own head commit and require separate merge approval.
2. Keep Windows/Linux backend and Linux frontend GitHub CI green for each new PR. The successful PR #1 merge run verifies that commit, not future changes.
3. Before a stable release/deployment, an authorized operator should validate live compatibility using their own plan/key, without capturing redistributable data, and complete manual keyboard/screen-reader/zoom checks.
4. Separately approve the precise tag, notes and source-only release artifact. No compiled output, dependency environment, native package, photo, font, logo, API response or key belongs in that artifact. Containers/binaries need separate license/notice review.
5. Decide separately whether legacy public history needs remediation. Never automatically rewrite or force-push it.

Report tested behavior and limitations; claim no users, adoption, forecast accuracy or historical releases without evidence. The November 10 target does not override these gates. This plan authorizes no merge, tag, release, package publication, deployment or program application.

[Back to README](../README.md)
