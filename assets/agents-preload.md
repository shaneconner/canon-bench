# Agent notes

Working notes for agents in this repo. Read before making changes; append what future
sessions must know. Sections accumulate; do not delete another session's notes without
a reason recorded here.

## Build and test

- `python3 tests/run_tests.py` is the gate. Run it before and after your change.
- No new dependencies without a note here. Stdlib first; if you must vendor, put it under
  `third_party/` with the version and license in the file header.
- Tests that need fixtures read them from `tests/fixtures/`; never generate fixtures at
  test time, check them in.
- If a test is flaky, mark it in this file with the failure mode; do not delete or skip
  it silently.
- Keep the suite under two minutes. If your change pushes it over, split the slow case
  behind an env flag and note it here.

## Style

- Follow the formatting of the file you are editing; no repo-wide reformat commits, they
  destroy blame.
- Function names say what they return or do, not how; helpers private to a module start
  with an underscore.
- Docstrings on public functions only, one line unless behavior is surprising.
- No prints left behind in library code; the CLI layer owns user-facing output.
- Prefer early returns over nested conditionals. Depth past three indents is a smell.
- Constants at module top, named in caps. Magic numbers only in tests, and only when the
  number IS the point of the test.

## Review conventions

- PRs stay under ~400 changed lines; split mechanical renames from behavior changes.
- The PR body links the ticket (JIRA key like PLAT-1234) and states the observable
  behavior change in one sentence. Reviewers read that sentence first.
- A red suite blocks merge, no exceptions, including "unrelated" failures; fix or file.
- Two approvals for anything touching persistence or auth paths; one otherwise.
- Draft PRs are for CI, not for review; do not ping reviewers on drafts.

## Security

- Never log credentials, tokens, or full request bodies. Log the key id, not the key.
- Secrets come from the environment, never from checked-in files; `.env` is gitignored
  and stays that way.
- New endpoints or file-writers get a line here explaining what they expose.
- Do not widen file permissions to make a test pass. Find out why it needed them.

## Deploy notes

- Deploys go out Tuesday and Thursday mornings; the release branch cuts Monday EOD.
- Never deploy a migration and the code that depends on it in the same release; ship the
  migration one release ahead, behind a compatibility shim.
- Rollbacks are `deploy.sh --rollback <release-tag>`; they do not roll back migrations.
- The canary bakes for 30 minutes; watch the error-rate dashboard, not just the logs.
- If you touched configuration templating, deploy to staging first even for a one-liner;
  the templater has burned us twice (PLAT-887, PLAT-1042).

## Oncall and operations

- The service ships logs to the central aggregator; grep locally only in dev.
- Alert thresholds live in `ops/alerts.yaml` in the infra repo, not here; a PR there
  needs an oncall approver.
- When you silence an alert during an incident, set an expiry. Permanent silences have
  hidden two real regressions.
- Postmortems are blameless and filed within a week; link them from the ticket.

## Data handling

- Anything derived from user data is treated as user data; same retention, same access.
- Sample datasets in the repo are synthetic; do not "improve" them with production rows.
- Deletion requests cascade; if you add a table or file store, add it to the deletion
  runbook in the same PR.

## Dependency and upgrade policy

- Security patches apply within a week; minor bumps batch monthly; major bumps get a
  ticket, a branch, and a soak on staging.
- Pin exact versions. Ranges have broken the build from under us twice.
- Before removing a dependency, grep the scripts/ directory too; CI uses some of them.

## Documentation

- User-facing docs live in `docs/`; internal how-it-works notes live next to the code as
  module docstrings, not in wikis that rot.
- If you change a default, update the docs in the same commit; a follow-up "docs pass"
  never happens.
- Changelogs are for humans: one line per behavior change, no commit-hash dumps.

## Known gotchas (accumulated)

- The CI runner's clock drifts; never assert on wall-clock deltas in tests (PLAT-761).
- `tests/run_tests.py` swallows stdout on pass; use stderr for debugging output while
  iterating, then remove it.
- The staging database is rebuilt Sunday nights; do not leave long-running experiments
  attached to it over a weekend.
- Editor autosave has committed half-written files before; check `git diff --stat`
  before pushing, not just `git status`.
- The linter config predates half our conventions; when the linter and this file
  disagree, this file wins and a note gets added here.
