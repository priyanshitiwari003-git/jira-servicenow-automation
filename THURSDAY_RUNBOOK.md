# Thursday Deployment Runbook

This is a living checklist for the weekly Thursday run.
Any new user-requested Thursday action must be appended here and followed in order.

## Weekly Steps

1. Verify runtime configuration
- Confirm Jira and ServiceNow credentials are valid.
- Confirm `RUN_ON_THURSDAY=True` and the expected `RUN_TIME`.
- Slack webhook is optional. If not available, generate the report text for manual posting.

2. Create parent update set for the week
- Generate parent name with format: `DEV-Q<quarter><year>-<MONTH>-WEEK<week_of_month>`.
- Example: `DEV-Q22026-JUNE-WEEK5`.
- Create and store parent sys_id for this run.

3. Fetch deployment candidates from Jira
- Fetch stories in `Ready for Deployment` status.
- Capture story key, summary, and assignee.

4. Find existing ServiceNow update sets for those stories
- Query `sys_update_set` for records where name contains each story key (example: `CET-2419`).
- Do not create new child update sets in this step.

5. Link existing matching update sets to the weekly parent
- For each matching existing record, set parent to the weekly parent sys_id.
- Ensure idempotent behavior: skip items already linked to the same parent.

6. Perform risk assessment on the selected update sets
- Inspect update contents from `sys_update_xml` for each linked update set.
- Report counts by action (insert_or_update, delete) and highlight delete-heavy sets.
- Flag risky items (for example: credential/property deletes, security changes, ACL/script/property updates).

7. Check for likely unrelated updates
- Compare update names/targets against Jira story context (key, summary, description keywords).
- Flag records that appear outside the expected business scope for manual review before production.

8. Build deployment report payload
- Include parent name and sys_id.
- Include developer names (assignees) and mapped stories.
- Include linked update sets with links.
- Include a summary of actual updates captured in child update sets (actions and key changed targets).
- For each child update set, write a risk narrative in this format: "This update is High/Medium/Low risk and can impact the system...".
- Include supporting import/artifact notes for customer updates using captured changed targets.
- Include risk findings and unrelated-update flags.

9. Update Confluence weekly deployment page
- Create or update the weekly Confluence page with deployment scope and risks.
- Use `CONFLUENCE_WEEKLY_TEMPLATE.md` as the base content.
- Include parent update set, story list, linked update sets, and go/no-go recommendation.
- Create one page per month using sprint name in title under parent page `https://tomtom.atlassian.net/wiki/spaces/ITSM/pages/644328917/Deployment`.
- Append weekly deployment details into that same monthly page.

10. Send or present report
- If Slack webhook is configured, send report to Slack.
- If Slack webhook is not configured, output the exact message text for manual posting.

11. Persist run outcome
- Record what was linked, what was skipped, and what is blocked.
- Keep this runbook updated with any new Thursday requirements.

## Current Parent Naming Rule

- `DEV-Q<quarter><year>-<MONTH>-WEEK<week_of_month>`

## Notes

- This runbook intentionally separates "find existing update sets" from "create new update sets".
- If production risk is high (especially many deletes), stop and request approval before promotion.
