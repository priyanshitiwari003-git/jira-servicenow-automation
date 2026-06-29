"""Confluence client for monthly deployment pages and weekly updates."""

from datetime import datetime
import re
from typing import Optional, Dict, Any

import requests
from requests.auth import HTTPBasicAuth

from src.config import ConfluenceConfig
from src.models import SyncResult
from src.logger import LoggerMixin


class ConfluenceClient(LoggerMixin):
    """Client for publishing deployment summaries to Confluence."""

    def __init__(self, config: ConfluenceConfig):
        self.config = config
        base = config.base_url.rstrip('/')
        self.base_url = base if base.endswith('/wiki') else f"{base}/wiki"
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(config.email, config.api_token)
        self.session.headers.update({'Content-Type': 'application/json', 'Accept': 'application/json'})

    def is_configured(self) -> bool:
        """Return True when Confluence integration should be active."""
        if not self.config.enabled:
            return False
        required = [
            self.config.base_url,
            self.config.email,
            self.config.api_token,
            self.config.space_key,
            self.config.parent_page_id,
        ]
        return all(required)

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    def _monthly_title(self, sprint_name: Optional[str], date_value: datetime) -> str:
        sprint_part = (sprint_name or 'No Sprint').strip()
        month_part = date_value.strftime('%B %Y')
        return f"{sprint_part} - {month_part} Deployment"

    def _get_or_create_monthly_page(self, sprint_name: Optional[str], date_value: datetime) -> Dict[str, Any]:
        title = self._monthly_title(sprint_name, date_value)
        existing = self._make_request(
            'GET',
            '/rest/api/content',
            params={
                'spaceKey': self.config.space_key,
                'title': title,
                'expand': 'version',
                'limit': 10,
            },
        )
        results = existing.get('results', [])
        if results:
            return results[0]

        body = (
            f"<p>Auto-generated monthly deployment page for <strong>{sprint_name or 'No Sprint'}</strong>.</p>"
            "<p>Weekly deployment entries are appended below.</p>"
        )
        created = self._make_request(
            'POST',
            '/rest/api/content',
            json={
                'type': 'page',
                'title': title,
                'ancestors': [{'id': str(self.config.parent_page_id)}],
                'space': {'key': self.config.space_key},
                'body': {
                    'storage': {
                        'value': body,
                        'representation': 'storage',
                    }
                },
            },
        )
        return created

    def _build_weekly_section(self, result: SyncResult) -> str:
        run_date = result.run_date or datetime.utcnow().strftime('%Y-%m-%d')
        story_rows = []
        story_keys_lower = [m.story_key.lower() for m in result.story_mappings if m.story_key]
        for mapping in result.story_mappings:
            update_sets = ', '.join(mapping.update_sets) if mapping.update_sets else 'None'
            assignee = mapping.assignee or 'Unassigned'
            story_rows.append(
                f"<tr><td>{mapping.story_key}</td><td>{mapping.story_summary}</td>"
                f"<td>{assignee}</td><td>{update_sets}</td></tr>"
            )

        if not story_rows:
            story_rows.append('<tr><td colspan="4">No linked story mappings in this run.</td></tr>')

        child_summary_items = []
        risk_rows = []
        for item in result.child_update_set_summaries:
            action_counts = item.get('action_counts', {})
            actions_text = ', '.join(f"{k}={v}" for k, v in sorted(action_counts.items())) or 'none'
            top_targets = item.get('top_targets', [])
            targets_text = ', '.join(top_targets) if top_targets else 'No target details captured'
            child_link = f"https://tomtomtest2.service-now.com/sys_update_set.do?sys_id={item.get('sys_id')}"
            delete_count = int(action_counts.get('delete', 0) or 0)
            total_changes = int(item.get('total_changes', 0) or 0)
            delete_ratio = (delete_count / total_changes) if total_changes else 0

            if delete_count >= 50 or delete_ratio >= 0.30:
                risk_level = 'High'
                risk_statement = 'This update is high risk and can impact the system if dependencies are not validated.'
            elif delete_count > 0 or total_changes >= 100:
                risk_level = 'Medium'
                risk_statement = 'This update is medium risk and should be validated in staging before production.'
            else:
                risk_level = 'Low'
                risk_statement = 'This update is low risk with limited system impact expected.'

            potentially_unrelated = []
            for target in top_targets:
                t = target.lower()
                if story_keys_lower and not any(story_key in t for story_key in story_keys_lower):
                    potentially_unrelated.append(target)

            unrelated_statement = ''
            if potentially_unrelated:
                unrelated_statement = (
                    f" Potentially unrelated to story scope: {', '.join(potentially_unrelated[:3])}."
                )

            risk_rows.append(
                f"<li><strong>{item.get('name')}</strong>: {risk_level} risk. "
                f"Delete updates found: {delete_count} out of {total_changes} total changes." 
                f"{unrelated_statement}</li>"
            )

            support_statement = (
                f"Supporting import/artifacts to verify: {targets_text}"
                if top_targets else
                "Supporting import/artifacts to verify: no explicit targets captured; validate related configuration records manually."
            )

            child_summary_items.append(
                f"<li><strong>{item.get('name')}</strong> - <strong>{risk_level} Risk</strong> "
                f"(<a href=\"{child_link}\">open</a>)<br/>"
                f"{risk_statement}<br/>"
                f"Captured changes: {total_changes} (actions: {actions_text}). "
                f"Delete updates found: {delete_count}.<br/>"
                f"{support_statement}</li>"
            )

        if not child_summary_items:
            child_summary_items.append('<li>No child update set changes were captured in this run.</li>')
        if not risk_rows:
            risk_rows.append('<li>No child update set risk details available for this run.</li>')

        parent_link = ''
        if result.parent_update_set_id:
            parent_link = (
                f"<p><strong>Parent Update Set:</strong> {result.parent_update_set_name} "
                f"(<a href=\"https://tomtomtest2.service-now.com/sys_update_set.do?sys_id={result.parent_update_set_id}\">open</a>)</p>"
            )

        return (
            f"<h2>Week of {run_date}</h2>"
            f"<p><strong>Status:</strong> {'Success' if result.success else 'Failed'}</p>"
            f"<p><strong>Total Stories:</strong> {result.total_stories} | "
            f"<strong>Synced:</strong> {result.synced_count} | "
            f"<strong>Skipped:</strong> {result.skipped_count} | "
            f"<strong>Failed:</strong> {result.failed_count}</p>"
            f"{parent_link}"
            "<h3>Child Update Set Deployment Summary</h3>"
            "<p>Summary below is generated from updates captured inside child update sets and includes risk and support-import guidance:</p>"
            f"<ul>{''.join(child_summary_items)}</ul>"
            "<table><tbody>"
            "<tr><th>Story</th><th>Summary</th><th>Developer</th><th>Update Sets</th></tr>"
            f"{''.join(story_rows)}"
            "</tbody></table>"
            "<p><strong>Risk Assessment:</strong></p>"
            f"<ul>{''.join(risk_rows)}</ul>"
        )

    def publish_weekly_deployment(self, result: SyncResult) -> Optional[str]:
        """Publish weekly deployment details into the monthly sprint page.

        Returns the page web URL if successful, otherwise None.
        """
        if not self.is_configured():
            self.logger.info('Confluence integration disabled or incomplete config; skipping page update')
            return None

        now = datetime.utcnow()
        monthly_page = self._get_or_create_monthly_page(result.sprint_name, now)
        page_id = monthly_page.get('id')

        page = self._make_request(
            'GET',
            f'/rest/api/content/{page_id}',
            params={'expand': 'body.storage,version,title'},
        )

        current_body = page.get('body', {}).get('storage', {}).get('value', '')
        section = self._build_weekly_section(result)
        week_header = f"Week of {result.run_date or now.strftime('%Y-%m-%d')}"

        # Replace this week's section if present, otherwise append a new section.
        pattern = rf"<h2>{re.escape(week_header)}</h2>[\s\S]*?(?=<h2>Week of |$)"
        if re.search(pattern, current_body):
            updated_body = re.sub(pattern, section, current_body, count=1)
            self.logger.info(f'Confluence weekly section updated for {week_header}')
        else:
            updated_body = f"{current_body}\n{section}"
            self.logger.info(f'Confluence weekly section appended for {week_header}')

        next_version = int(page.get('version', {}).get('number', 1)) + 1

        updated = self._make_request(
            'PUT',
            f'/rest/api/content/{page_id}',
            json={
                'id': str(page_id),
                'type': 'page',
                'title': page.get('title'),
                'version': {'number': next_version},
                'body': {
                    'storage': {
                        'value': updated_body,
                        'representation': 'storage',
                    }
                },
            },
        )

        webui = updated.get('_links', {}).get('webui', '')
        page_url = f"{self.base_url}{webui}" if webui else None
        self.logger.info(f'Confluence weekly deployment details published | page_id={page_id}')
        return page_url

    def close(self):
        self.session.close()
