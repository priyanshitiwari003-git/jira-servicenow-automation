# JIRA to ServiceNow Automation Agent

This repository contains an automated workflow that:
- Fetches update set links from ready-for-deployment stories in JIRA
- Adds those update sets to a parent record in ServiceNow
- Runs every Thursday at 9:00 AM UTC

## Components

- **GitHub Actions Workflow**: Scheduled workflow (`.github/workflows/thursday-automation.yml`)
- **JIRA Integration Script**: Fetches stories and update set links (`scripts/jira_fetch.py`)
- **ServiceNow Integration Script**: Adds update sets to parent records (`scripts/servicenow_update.py`)
- **Main Orchestrator**: Coordinates the workflow (`scripts/main.py`)
- **Utilities**: Helper functions for logging and error handling (`scripts/utils.py`)

## Quick Start

### 1. Add GitHub Secrets

Go to your repository Settings → Secrets and variables → Actions, and add:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `JIRA_URL` | JIRA instance URL | `https://your-company.atlassian.net` |
| `JIRA_USERNAME` | JIRA API username | `user@company.com` |
| `JIRA_API_TOKEN` | JIRA API token | (Get from https://id.atlassian.com/manage-profile/security/api-tokens) |
| `JIRA_PROJECT_KEY` | JIRA project key | `PROJ` |
| `JIRA_STATUS_FILTER` | Status to filter by | `Ready for Deployment` |
| `JIRA_UPDATE_SET_FIELD` | Custom field ID for update set links | `customfield_10050` |
| `SERVICENOW_URL` | ServiceNow instance URL | `https://dev12345.service-now.com` |
| `SERVICENOW_USERNAME` | ServiceNow API username | `api_user` |
| `SERVICENOW_PASSWORD` | ServiceNow API password | (Use a service account with API access) |
| `SERVICENOW_PARENT_TABLE` | Parent table name | `sn_chg_management_change` |
| `SERVICENOW_PARENT_ID` | Parent record ID | `CHG0123456` |
| `SERVICENOW_UPDATE_SET_FIELD` | Field name for update sets | `u_update_sets` |

### 2. Configure Workflow Schedule

Edit `.github/workflows/thursday-automation.yml` to customize:
- **Time**: Change the cron schedule (currently 9:00 AM UTC every Thursday)
- **Timezone**: Adjust if needed

### 3. Run Manually

To test the automation without waiting for Thursday:
1. Go to Actions → Thursday JIRA-ServiceNow Sync
2. Click "Run workflow" → "Run workflow"

## How It Works

1. **Trigger**: GitHub Actions runs every Thursday at 9:00 AM UTC
2. **JIRA Query**: Fetches all issues with status "Ready for Deployment"
3. **Extract Links**: Parses update set links from the configured custom field
4. **ServiceNow Update**: Adds new update sets to the parent record
5. **Logging**: Records all actions and errors
6. **Notification**: (Optional) Posts results to Slack or email

## Architecture

```
┌───────────────────────────────────────────────────────────────┐
│         GitHub Actions (Thursday 9:00 AM UTC)                 │
└───────────────────────────────┬───────────────────────────────┘
                                │
                                ▼
                ┌───────────────────────────────────┐
                │   main.py (Orchestrator)          │
                └────────────────┬────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
            ┌──────────────────┐    ┌──────────────────────────────┐
            │  jira_fetch      │    │  servicenow_update           │
            └────────┬─────────┘    └─────────┬────────────────────┘
                     ▼                         ▼
                 JIRA API          ServiceNow API
```

## Troubleshooting

### Check Workflow Logs
1. Go to your repository → Actions
2. Click on the latest "Thursday JIRA-ServiceNow Sync" run
3. View logs in "Run workflow" step

### Common Issues

**"401 Unauthorized" from JIRA**
- Verify JIRA_USERNAME and JIRA_API_TOKEN are correct
- API token may have expired; generate a new one

**"404 Not Found" from ServiceNow**
- Check SERVICENOW_PARENT_ID exists
- Verify SERVICENOW_PARENT_TABLE name is correct

**No update sets found**
- Verify JIRA_UPDATE_SET_FIELD contains URLs
- Check JIRA_STATUS_FILTER matches your status name exactly
- Run a manual JIRA query to verify data exists

## Security Best Practices

✅ All credentials stored in GitHub Secrets (encrypted)  
✅ No credentials in code or logs  
✅ Use service accounts (not personal accounts)  
✅ Rotate API tokens regularly  
✅ Enable audit logging in both JIRA and ServiceNow  
✅ Restrict workflow permissions in repository settings  

## Advanced Configuration

### Custom JIRA JQL Query
Edit `scripts/jira_fetch.py` to modify the JQL query for more specific filtering.

### Email Notifications
Add email configuration to `scripts/main.py` to send results via email.

### Slack Integration
Add webhook URL as a GitHub Secret and configure in `scripts/utils.py`.

## Support

For issues or questions:
1. Check GitHub Actions logs
2. Review JIRA and ServiceNow API documentation
3. Open a GitHub Issue in this repository

## License

MIT
