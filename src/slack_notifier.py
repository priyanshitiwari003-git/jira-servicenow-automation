"""Slack integration for sending deployment reports."""

import requests
from typing import Optional, Dict, Any
from src.config import SlackConfig, ServiceNowConfig
from src.models import SyncResult
from src.logger import LoggerMixin


class SlackNotifier(LoggerMixin):
    """Sends deployment reports to Slack."""

    def __init__(self, config: SlackConfig, servicenow_config: ServiceNowConfig):
        """Initialize Slack notifier.

        Args:
            config: Slack configuration
            servicenow_config: ServiceNow configuration
        """
        self.config = config
        self.webhook_url = config.webhook_url
        self.servicenow_url = servicenow_config.instance_url.rstrip('/')

    def send_deployment_report(self, result: SyncResult) -> bool:
        """Send deployment report to Slack channel.

        Args:
            result: SyncResult with deployment details

        Returns:
            True if successful
        """
        try:
            payload = self._build_message(result)
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            self.logger.info(f"Deployment report sent to Slack | status_code={response.status_code}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send Slack message: {e}")
            return False

    @staticmethod
    def _truncate(value: str, length: int) -> str:
        if len(value) <= length:
            return value
        return value[: length - 3] + "..."

    def _build_child_updates_table(self, result: SyncResult) -> Optional[str]:
        """Build a table-style text block for child update sets added this week."""
        rows = []
        for mapping in result.story_mappings:
            developer = mapping.assignee or "Unassigned"
            for update_set in mapping.update_sets:
                rows.append(
                    (
                        self._truncate(update_set, 34),
                        self._truncate(developer, 18),
                        self._truncate(mapping.story_key, 12),
                        self._truncate(mapping.story_summary, 42),
                    )
                )

        if not rows:
            return None

        header = "| Child Update Set                    | Developer          | Story       | Story Summary                              |"
        sep = "|-------------------------------------|--------------------|-------------|--------------------------------------------|"
        lines = [header, sep]
        for update_set, developer, story_key, story_summary in rows:
            lines.append(
                f"| {update_set:<35} | {developer:<18} | {story_key:<11} | {story_summary:<42} |"
            )

        table_text = "\n".join(lines)
        # Slack section text limit guard (~3000 chars)
        if len(table_text) > 2800:
            table_text = table_text[:2750] + "\n... (truncated)"

        return table_text

    def _build_message(self, result: SyncResult) -> Dict[str, Any]:
        """Build Slack message payload.

        Args:
            result: SyncResult

        Returns:
            Slack message payload
        """
        fields = [
            {"type": "mrkdwn", "text": f"*Status:*\n{'✅ Success' if result.success else '❌ Failed'}"},
            {"type": "mrkdwn", "text": f"*Total Stories:*\n{result.total_stories}"},
            {"type": "mrkdwn", "text": f"*Synced:*\n{result.synced_count}"},
            {"type": "mrkdwn", "text": f"*Failed:*\n{result.failed_count}"},
            {"type": "mrkdwn", "text": f"*Skipped:*\n{result.skipped_count}"},
        ]

        if result.sprint_name:
            fields.insert(0, {"type": "mrkdwn", "text": f"*Sprint:*\n{result.sprint_name}"})

        if result.parent_update_set_name:
            fields.append({"type": "mrkdwn", "text": f"*Parent Update Set:*\n{result.parent_update_set_name}"})

        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*📦 Deployment Report - {result.sprint_name or 'Ready for Deployment'}*"}},
            {"type": "section", "fields": fields},
        ]

        if result.parent_update_set_id:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View in ServiceNow"},
                        "url": f"{self.servicenow_url}/nav_to.do?uri=table/sn_chg_management_update_set.do?sys_id={result.parent_update_set_id}"
                    }
                ]
            })

        child_table = self._build_child_updates_table(result)
        if child_table:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Child Update Sets Added To Parent (This Week)*\n```" + child_table + "```"
                }
            })
            blocks.append({"type": "divider"})

        for mapping in result.story_mappings:
            mapping_lines = [
                f"*Story:* {mapping.story_key}",
                f"*Summary:* {mapping.story_summary}",
                f"*Update Sets:* {', '.join(mapping.update_sets) if mapping.update_sets else 'None'}"
            ]
            if mapping.assignee:
                mapping_lines.append(f"*Assigned To:* {mapping.assignee}")

            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": "\n".join(mapping_lines)}
            })
            blocks.append({"type": "divider"})

        return {"blocks": blocks}

    def send_error_notification(self, error_message: str, sprint_name: Optional[str] = None) -> bool:
        """Send error notification to Slack.

        Args:
            error_message: Error message
            sprint_name: Optional sprint name

        Returns:
            True if successful
        """
        try:
            payload = {
                "blocks": [
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*❌ Deployment Agent Error - {sprint_name or 'Unknown Sprint'}*"}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"*Error:*\n{error_message}"}}
                ]
            }
            response = requests.post(self.webhook_url, json=payload)
            response.raise_for_status()
            self.logger.info("Error notification sent to Slack")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send error notification: {e}")
            return False
