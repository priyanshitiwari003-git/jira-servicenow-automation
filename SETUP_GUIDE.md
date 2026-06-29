# Complete .env Configuration Guide

This guide walks you through getting all the credentials and configuring your `.env` file step by step.

## Table of Contents
1. [Jira Configuration](#jira-configuration)
2. [ServiceNow Configuration](#servicenow-configuration)
3. [Slack Webhook Configuration](#slack-webhook-configuration)
4. [Final .env File](#final-env-file)
5. [Verify Configuration](#verify-configuration)

---

## Jira Configuration

### Step 1: Get Your Jira Base URL

1. Go to your Jira instance (e.g., `https://mycompany.atlassian.net`)
2. Copy the URL from your browser's address bar
3. **Important**: Use ONLY the base URL (without `/browse`, `/projects`, etc.)

**Example:**
```
✅ Correct: https://mycompany.atlassian.net
❌ Wrong:  https://mycompany.atlassian.net/browse/PROJ-123
```

### Step 2: Get Your Jira Email (Username)

This is your Jira login email:
```
JIRA_USERNAME=john.doe@mycompany.com
```

### Step 3: Create Jira API Token

**You CANNOT use your password. You MUST create an API token.**

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **"Create API token"** button
3. Enter a name (e.g., `ServiceNow Agent`)
4. Click **"Create"**
5. **Copy the token immediately** (you won't see it again!)

```
JIRA_API_TOKEN=aAbBcCdDeEfFgGhHiIjJkK
```

**Screenshot Guide:**
```
https://id.atlassian.com/manage-profile/security/api-tokens
    ↓
[Create API token] button (top right)
    ↓
Name: "ServiceNow Agent"
    ↓
[Create] button
    ↓
Copy token from the dialog
    ↓
Save in .env as JIRA_API_TOKEN
```

### Step 4: Find Your Jira Project Key

1. Go to your Jira instance
2. Click on your project
3. Look at the URL: `https://mycompany.atlassian.net/browse/PROJ-123`
4. The project key is the letters before the dash: **PROJ**

```
JIRA_PROJECT_KEY=PROJ
```

**Common examples:**
- `DEV` (Development)
- `INFRA` (Infrastructure)
- `DEPLOY` (Deployment)
- `PLATFORM` (Platform)

### Step 5: Find Your Jira Board ID

1. Go to your project
2. Click on **"Backlog"** or **"Board"** tab
3. Look at the URL: `https://mycompany.atlassian.net/software/c/projects/PROJ/boards/1/backlog`
4. The board ID is the number after `/boards/`: **1**

```
JIRA_BOARD_ID=1
```

**Alternative method:**
- If you can't find it in URL, go to Board Settings → look for "Board ID" or "Sprint Board"

### Step 6: Story Status Name

This should match the exact status in your workflow. Most common:
```
JIRA_STORY_STATUS=Ready for Deployment
```

**Check your actual status:**
1. Go to a story in your project
2. Look at the "Status" dropdown
3. Find the exact name (case-sensitive!)

**Common variations:**
- `Ready for Deployment` (with spaces)
- `ReadyForDeployment` (no spaces)
- `Ready-for-Deployment` (with dashes)
- `READY_FOR_DEPLOYMENT` (all caps)

**Copy the EXACT text from your system.**

### Example Jira Configuration
```
JIRA_BASE_URL=https://mycompany.atlassian.net
JIRA_USERNAME=john.doe@mycompany.com
JIRA_API_TOKEN=aAbBcCdDeEfFgGhHiIjJkK
JIRA_PROJECT_KEY=PROJ
JIRA_BOARD_ID=1
JIRA_STORY_STATUS=Ready for Deployment
```

---

## ServiceNow Configuration

### Step 1: Get Your ServiceNow Instance URL

1. Log into ServiceNow
2. Copy the URL from your browser: `https://mycompany.service-now.com`
3. **Important**: Use ONLY the base instance URL

```
SN_INSTANCE_URL=https://mycompany.service-now.com
```

**Do NOT include:**
- `/home`
- `/nav_to.do`
- `/api/now/table`
- `/lists`

### Step 2: Create a ServiceNow Service Account

**It's best practice to create a dedicated service account instead of using your personal account.**

1. Go to ServiceNow → Admin → System Security → Users
2. Click **"New"** button
3. Fill in the form:
   ```
   First Name: ServiceNow
   Last Name: Agent
   User name: servicenow_agent
   Password: [Generate a strong password]
   ```
4. Click **"Save"**
5. Assign role: `admin` or `itil` (depending on your needs)

**If you don't have admin access:**
- Ask your ServiceNow administrator to create the account
- Provide them this info:
  - **Username**: `servicenow_agent`
  - **Required Roles**: `admin` or `itil`
  - **Description**: For Jira-ServiceNow deployment automation

```
SN_USERNAME=servicenow_agent
SN_PASSWORD=YourStrongPassword123!
```

### Step 3: Find Your Update Set Table Name

The table where update sets are stored. Usually:
```
SN_TABLE=sn_chg_management_update_set
```

**If you're using a different table:**
1. Go to ServiceNow → System Definition → Tables
2. Search for your table
3. Copy the exact table name

**Common tables:**
- `sn_chg_management_update_set` (Change Management)
- `sys_update_set` (Core Update Sets)
- `cmdb_ci_service` (Services)

### Step 4: Test ServiceNow Connection

Before adding to `.env`, test the connection:

```bash
curl -u servicenow_agent:YourPassword \
  "https://mycompany.service-now.com/api/now/table/sn_chg_management_update_set?sysparm_limit=1"
```

**Expected response:**
```json
{
  "result": [
    {
      "sys_id": "...",
      "name": "...",
      ...
    }
  ]
}
```

**If you get an error:**
- Check username/password
- Verify ServiceNow instance URL
- Ensure user has correct role permissions

### Example ServiceNow Configuration
```
SN_INSTANCE_URL=https://mycompany.service-now.com
SN_USERNAME=servicenow_agent
SN_PASSWORD=YourStrongPassword123!
SN_TABLE=sn_chg_management_update_set
```

---

## Slack Webhook Configuration

### Step 1: Create an Incoming Webhook in Slack

1. Open Slack and go to the workspace where you want deployment reports
2. Open **Apps** and search for **Incoming Webhooks**
3. Click **Add to Slack** or **Configure** for the channel
4. Choose the target channel and click **Add Incoming Webhooks integration**

### Step 2: Copy the Webhook URL

1. After configuring the webhook, copy the generated URL
2. Save it immediately in your `.env`:
   ```
  SLACK_WEBHOOK_URL=https://example.com/slack-webhook-url
   ```

### Step 3: Test the Webhook

Run this command to test:

```bash
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Test message from Jira-ServiceNow Deployment Agent"
  }' \
  "YOUR_SLACK_WEBHOOK_URL_HERE"
```

**If it works:**
- You'll see the message appear in Slack
- Your webhook is configured correctly

### Example Slack Configuration
```
SLACK_WEBHOOK_URL=https://example.com/slack-webhook-url
```

---

## Agent Configuration

These settings control how the agent runs:

```
# What is the agent name?
AGENT_NAME=Jira-ServiceNow Deployment Agent

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Run on Thursdays?
RUN_ON_THURSDAY=True

# What time to run? (HH:MM in 24-hour format)
RUN_TIME=09:00

# Preview mode (True = don't actually create anything)
DRY_RUN=False

# File paths (where to store logs and state)
STATE_FILE_PATH=./state/agent_state.json
LOG_FILE_PATH=./logs/agent.log
```

**Time Format Examples:**
```
RUN_TIME=09:00   → 9:00 AM
RUN_TIME=14:30   → 2:30 PM
RUN_TIME=20:00   → 8:00 PM
```

---

## Final .env File

Here's a complete example with all values filled in:

```bash
# ============================================================================
# JIRA CONFIGURATION
# ============================================================================
JIRA_BASE_URL=https://mycompany.atlassian.net
JIRA_USERNAME=john.doe@mycompany.com
JIRA_API_TOKEN=aAbBcCdDeEfFgGhHiIjJkKlMnOpQrStUvWxYz
JIRA_PROJECT_KEY=PROJ
JIRA_BOARD_ID=1
JIRA_STORY_STATUS=Ready for Deployment

# ============================================================================
# SERVICENOW CONFIGURATION
# ============================================================================
SN_INSTANCE_URL=https://mycompany.service-now.com
SN_USERNAME=servicenow_agent
SN_PASSWORD=YourStrongPassword123!
SN_TABLE=sn_chg_management_update_set

# ============================================================================
# SLACK CONFIGURATION
# ============================================================================
SLACK_WEBHOOK_URL=https://example.com/slack-webhook-url

# ============================================================================
# AGENT CONFIGURATION
# ============================================================================
AGENT_NAME=Jira-ServiceNow Deployment Agent
LOG_LEVEL=INFO
RUN_ON_THURSDAY=True
RUN_TIME=09:00
DRY_RUN=False

# ============================================================================
# STATE & STORAGE
# ============================================================================
STATE_FILE_PATH=./state/agent_state.json
LOG_FILE_PATH=./logs/agent.log
```

---

## Verify Configuration

### Step 1: Copy and Edit .env

```bash
# Copy the template
cp .env.example .env

# Edit with your credentials
nano .env
# or
vi .env
# or use your favorite editor (VS Code, Sublime, etc.)
```

### Step 2: Create Directories

```bash
mkdir -p state logs
```

### Step 3: Test Each Connection

#### Test Jira Connection:
```bash
python -c "
from src.config import AppConfig
from src.jira_client import JiraClient

config = AppConfig.from_env()
client = JiraClient(config.jira)
stories = client.fetch_ready_for_deployment_stories()
print(f'✅ Jira connected! Found {len(stories)} stories')
"
```

#### Test ServiceNow Connection:
```bash
python -c "
from src.config import AppConfig
from src.servicenow_client import ServiceNowClient

config = AppConfig.from_env()
client = ServiceNowClient(config.servicenow)
update_sets = client.get_all_update_sets()
print(f'✅ ServiceNow connected! Found {len(update_sets)} update sets')
"
```

#### Test Slack Webhook:
```bash
python -c "
from src.config import AppConfig
from src.slack_notifier import SlackNotifier
from src.models import SyncResult

config = AppConfig.from_env()
notifier = SlackNotifier(config.slack, config.servicenow)
result = SyncResult(success=True, total_stories=0)
notifier.send_error_notification('Test message from agent')
print('✅ Slack webhook working!')
"
```

### Step 4: Dry Run Test

Test without creating anything:

```bash
python main.py --run --dry-run
```

**You should see:**
```
✅ Starting Jira-ServiceNow Deployment Agent
[DRY RUN] Would create parent update set
[DRY RUN] Would create child update set
✅ Deployment sync finished
```

### Step 5: Run for Real

Once dry run works:

```bash
python main.py --run
```

---

## Troubleshooting

### Error: "Configuration error: This field is required"

**Solution**: Check that all REQUIRED fields are filled in `.env`:
- `JIRA_BASE_URL`
- `JIRA_USERNAME`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`
- `SN_INSTANCE_URL`
- `SN_USERNAME`
- `SN_PASSWORD`
- `SLACK_WEBHOOK_URL`

### Error: "Authentication failed" from Jira

**Causes:**
- ❌ Wrong API token
- ❌ Using password instead of API token
- ❌ Token was revoked
- ❌ Wrong email address

**Solution:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Delete old token
3. Create new token
4. Update `.env`

### Error: "Authentication failed" from ServiceNow

**Causes:**
- ❌ Wrong username or password
- ❌ User account disabled
- ❌ User doesn't have required role

**Solution:**
1. Test login directly to ServiceNow
2. Check user has `admin` or `itil` role
3. Ask ServiceNow admin to verify account

### Error: "Failed to send Slack message"

**Causes:**
- ❌ Wrong webhook URL
- ❌ Webhook expired
- ❌ Network connectivity issue

**Solution:**
1. Regenerate webhook in Slack
2. Copy new URL to `.env`
3. Test with curl command (see above)

### Error: "No stories found"

**Causes:**
- ❌ No stories with "Ready for Deployment" status
- ❌ Wrong project key
- ❌ Wrong status name

**Solution:**
1. Go to your Jira project
2. Check the exact status name
3. Verify there are actually stories with that status
4. Update `.env` with correct values

### Error: "No update set links found"

**Causes:**
- ❌ Comments don't contain update set links
- ❌ Links in unsupported format

**Solution:**
1. Add update set links to Jira comments using supported formats:
   ```
   UpdateSet: us_name
   https://instance.service-now.com/...?sys_id=xxxxx
   ```
2. Verify links are in comments (not description)

---

## Security Best Practices

### 1. Protect Your .env File

```bash
# Make sure .env is not committed to Git
grep ".env" .gitignore

# Set proper file permissions (Linux/Mac)
chmod 600 .env
```

### 2. Use Service Accounts

- ✅ DO: Create dedicated service account in ServiceNow
- ❌ DON'T: Use your personal account credentials

### 3. Rotate Credentials Regularly

- Jira API tokens: Generate new one monthly
- ServiceNow password: Change every 90 days
- Slack webhook: Regenerate annually

### 4. Restrict Access

- Limit who can access the `.env` file
- Store it securely (not in cloud storage)
- Use environment variables in production

### 5. Monitor Logs

Check `logs/agent.log` regularly for:
- Failed authentication attempts
- Unusual activity
- Performance issues

---

## Next Steps

1. ✅ Configure all credentials in `.env`
2. ✅ Run `python main.py --run --dry-run` to test
3. ✅ Verify Slack message appears in channel
4. ✅ Run `python main.py --run` to create first update sets
5. ✅ Set up scheduling: `python main.py --schedule`
6. ✅ Follow `THURSDAY_RUNBOOK.md` for weekly execution and append new Thursday requirements

---

## Need Help?

If you get stuck:

1. **Check logs**: `tail -f logs/agent.log`
2. **Test individually**: Test each service separately
3. **Verify credentials**: Double-check each value
4. **Ask for help**: Contact your Jira/ServiceNow/Slack admin

---

**You're all set! Happy deploying! 🚀**
