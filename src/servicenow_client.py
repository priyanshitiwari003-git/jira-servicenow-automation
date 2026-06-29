"""ServiceNow API client for creating and managing update sets."""

import collections
import requests
from typing import List, Optional, Dict, Any
from requests.auth import HTTPBasicAuth
from src.config import ServiceNowConfig
from src.models import UpdateSet
from src.logger import LoggerMixin


class ServiceNowClient(LoggerMixin):
    """Client for interacting with ServiceNow API."""

    def __init__(self, config: ServiceNowConfig):
        """Initialize ServiceNow client.

        Args:
            config: ServiceNow configuration
        """
        self.config = config
        self.instance_url = config.instance_url.rstrip('/')
        self.auth = HTTPBasicAuth(config.username, config.password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({'Content-Type': 'application/json'})
        self.table = config.table

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make API request to ServiceNow.

        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters

        Returns:
            Response JSON

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.instance_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            self.logger.error(f"ServiceNow API error: {e}")
            raise

    def create_parent_deployment_set(self, parent_name: str, sprint_name: Optional[str] = None,
                                     dry_run: bool = False) -> Optional[str]:
        """Create a parent deployment update set.

        Args:
            parent_name: Parent update set name
            sprint_name: Current sprint name
            dry_run: If True, don't actually create

        Returns:
            Created sys_id or None
        """
        if dry_run:
            self.logger.info(f"[DRY RUN] Would create parent update set | name={parent_name}")
            return f"dry_run_{parent_name}"

        payload = {
            'name': parent_name,
            'description': f"Parent deployment set for {sprint_name}" if sprint_name else "Parent deployment update set",
            'type': 'parent',
            'state': 'in_progress',
        }

        try:
            response = self._make_request(
                'POST',
                f'/api/now/table/{self.table}',
                json=payload
            )

            result = response.get('result', {})
            sys_id = result.get('sys_id')

            self.logger.info(f"Created parent update set | name={parent_name} | sys_id={sys_id}")
            return sys_id

        except Exception as e:
            self.logger.error(f"Failed to create parent update set {parent_name}: {e}")
            return None

    def create_child_update_set(self, update_set_name: str, parent_sys_id: str,
                               jira_story_key: Optional[str] = None,
                               jira_story_summary: Optional[str] = None,
                               dry_run: bool = False) -> Optional[str]:
        """Create a child update set under a parent.

        Args:
            update_set_name: Child update set name/ID
            parent_sys_id: Parent update set sys_id
            jira_story_key: Reference to Jira story
            jira_story_summary: Jira story summary
            dry_run: If True, don't actually create

        Returns:
            Created sys_id or None
        """
        if dry_run:
            self.logger.info(f"[DRY RUN] Would create child update set | name={update_set_name} | parent={parent_sys_id}")
            return f"dry_run_{update_set_name}"

        payload = {
            'name': update_set_name,
            'description': f"Deployed from {jira_story_key}: {jira_story_summary}" if jira_story_key else "Child update set",
            'type': 'child',
            'state': 'in_progress',
            'parent': parent_sys_id,
        }

        # Add custom field for Jira tracking
        if jira_story_key:
            payload['u_jira_story_key'] = jira_story_key

        try:
            response = self._make_request(
                'POST',
                f'/api/now/table/{self.table}',
                json=payload
            )

            result = response.get('result', {})
            sys_id = result.get('sys_id')

            self.logger.info(f"Created child update set | name={update_set_name} | parent_sys_id={parent_sys_id} | sys_id={sys_id}")
            return sys_id

        except Exception as e:
            self.logger.error(f"Failed to create child update set {update_set_name}: {e}")
            return None

    def get_update_set(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an update set by name.

        Args:
            name: Update set name

        Returns:
            Update set data or None
        """
        try:
            response = self._make_request(
                'GET',
                f'/api/now/table/{self.table}',
                params={'sysparm_query': f'name={name}', 'sysparm_limit': 1}
            )

            results = response.get('result', [])
            if results:
                return results[0]
            return None
        except Exception as e:
            self.logger.error(f"Failed to get update set {name}: {e}")
            return None

    def get_update_set_by_sys_id(self, sys_id: str) -> Optional[Dict[str, Any]]:
        """Get an update set by sys_id.

        Args:
            sys_id: ServiceNow system ID

        Returns:
            Update set data or None
        """
        try:
            response = self._make_request(
                'GET',
                f'/api/now/table/{self.table}/{sys_id}'
            )
            return response.get('result')
        except Exception as e:
            self.logger.error(f"Failed to get update set {sys_id}: {e}")
            return None

    def get_child_update_set_summaries(self, parent_sys_id: str, max_targets: int = 5) -> List[Dict[str, Any]]:
        """Summarize captured updates for child update sets under a parent.

        Args:
            parent_sys_id: Parent update set sys_id
            max_targets: Number of changed targets to include per child

        Returns:
            List of per-child summaries with action counts and top changed targets
        """
        summaries: List[Dict[str, Any]] = []
        try:
            children_resp = self._make_request(
                'GET',
                f'/api/now/table/{self.table}',
                params={
                    'sysparm_query': f'parent={parent_sys_id}^ORDERBYDESCsys_created_on',
                    'sysparm_fields': 'sys_id,name,state,sys_created_on',
                    'sysparm_limit': 200,
                }
            )
            children = children_resp.get('result', [])

            for child in children:
                child_id = child.get('sys_id')
                xml_resp = self._make_request(
                    'GET',
                    '/api/now/table/sys_update_xml',
                    params={
                        'sysparm_query': f'update_set={child_id}',
                        'sysparm_fields': 'action,target_name,name,sys_id',
                        'sysparm_limit': 1000,
                    }
                )
                rows = xml_resp.get('result', [])

                action_counts = collections.Counter()
                target_counts = collections.Counter()
                for row in rows:
                    action = (row.get('action') or 'unknown').lower()
                    action_counts[action] += 1
                    target = (row.get('target_name') or row.get('name') or '').strip()
                    if target:
                        target_counts[target] += 1

                summaries.append({
                    'sys_id': child_id,
                    'name': child.get('name'),
                    'state': child.get('state'),
                    'created_on': child.get('sys_created_on'),
                    'total_changes': len(rows),
                    'action_counts': dict(action_counts),
                    'top_targets': [name for name, _ in target_counts.most_common(max_targets)],
                })

        except Exception as e:
            self.logger.error(f"Failed to summarize child update sets for parent {parent_sys_id}: {e}")

        return summaries

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
