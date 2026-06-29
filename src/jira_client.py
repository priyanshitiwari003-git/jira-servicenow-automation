"""Jira API client for fetching stories and extracting update set links from comments."""

import requests
import re
from typing import List, Optional
from datetime import datetime
from requests.auth import HTTPBasicAuth
from src.config import JiraConfig
from src.models import JiraStory, JiraComment
from src.logger import LoggerMixin


class JiraClient(LoggerMixin):
    """Client for interacting with Jira API."""

    def __init__(self, config: JiraConfig):
        """Initialize Jira client.

        Args:
            config: Jira configuration
        """
        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self.auth = HTTPBasicAuth(config.username, config.api_token)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.session.headers.update({'Accept': 'application/json'})

    def _make_request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make API request to Jira.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional request parameters

        Returns:
            Response JSON

        Raises:
            requests.RequestException: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            response = getattr(e, 'response', None)
            if response is not None:
                self.logger.error(f"Jira API error: {e} | status={response.status_code} | body={response.text}")
            else:
                self.logger.error(f"Jira API error: {e}")
            raise

    def fetch_ready_for_deployment_stories(self) -> List[JiraStory]:
        """Fetch stories in 'Ready for Deployment' status.

        Returns:
            List of JiraStory objects with update set links from comments
        """
        jql = f'project = "{self.config.project_key}" AND status = "{self.config.story_status}" ORDER BY updated DESC'
        self.logger.info(f"Fetching stories in '{self.config.story_status}' status | jql={jql}")

        stories = []
        max_results = 50
        next_page_token = None

        while True:
            try:
                payload = {
                    'jql': jql,
                    'maxResults': max_results,
                    'fields': ['summary', 'description', 'status', 'assignee', 'reporter', 'labels', 'created', 'updated']
                }
                if next_page_token:
                    payload['nextPageToken'] = next_page_token

                response = self._make_request(
                    'POST',
                    '/rest/api/3/search/jql',
                    json=payload
                )

                for issue in response.get('issues', []):
                    story = self._parse_story(issue)
                    if story:
                        # Fetch comments to extract update set links
                        story.comments = self.get_story_comments(story.key)
                        story.update_set_links = self._extract_update_set_links(story)
                        stories.append(story)

                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break

            except Exception as e:
                self.logger.error(f"Error fetching stories: {e}")
                break

        self.logger.info(f"Successfully fetched {len(stories)} stories in '{self.config.story_status}' status")
        return stories

    def _parse_story(self, issue: dict) -> Optional[JiraStory]:
        """Parse Jira issue to JiraStory model.

        Args:
            issue: Jira issue data

        Returns:
            JiraStory object or None if parsing fails
        """
        try:
            fields = issue.get('fields', {})
            assignee = fields.get('assignee') or {}
            reporter = fields.get('reporter') or {}

            story = JiraStory(
                key=issue.get('key'),
                summary=fields.get('summary', ''),
                description=self._to_text(fields.get('description')),
                status=fields.get('status', {}).get('name', 'Unknown'),
                created=fields.get('created'),
                updated=fields.get('updated'),
                assignee=assignee.get('displayName'),
                reporter=reporter.get('displayName'),
                labels=fields.get('labels', []),
                custom_fields=fields
            )
            return story
        except Exception as e:
            self.logger.warning(f"Failed to parse story {issue.get('key')}: {e}")
            return None

    def get_story_comments(self, story_key: str) -> List[JiraComment]:
        """Get all comments for a story.

        Args:
            story_key: Jira story key

        Returns:
            List of JiraComment objects
        """
        try:
            response = self._make_request(
                'GET',
                f'/rest/api/3/issue/{story_key}',
                params={'fields': 'comment'}
            )

            comments = []
            for comment_data in response.get('fields', {}).get('comment', {}).get('comments', []):
                comment = JiraComment(
                    id=comment_data.get('id'),
                    author=comment_data.get('author', {}).get('displayName'),
                    body=self._to_text(comment_data.get('body')),
                    created=comment_data.get('created'),
                    updated=comment_data.get('updated')
                )
                comments.append(comment)

            return comments
        except Exception as e:
            self.logger.warning(f"Failed to get comments for {story_key}: {e}")
            return []

    def _to_text(self, value) -> str:
        """Convert Jira rich-text (ADF) or plain values to a best-effort text string."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            parts = [self._to_text(item) for item in value]
            return "\n".join(part for part in parts if part).strip()
        if isinstance(value, dict):
            # ADF nodes usually store text in `text` and children in `content`.
            text = value.get('text', '')
            content = self._to_text(value.get('content', []))
            if text and content:
                return f"{text}\n{content}".strip()
            return (text or content).strip()
        return str(value)

    def _extract_update_set_links(self, story: JiraStory) -> List[str]:
        """Extract ServiceNow update set links from story comments.

        Looks for patterns:
        - Full URLs: https://instance.service-now.com/...?sys_id=xxxxx
        - Update set names: us_xxxxx or similar
        - Manual references: "UpdateSet: xxxxx"

        Args:
            story: JiraStory object

        Returns:
            List of unique update set identifiers
        """
        update_sets = set()

        # Check description
        if story.description:
            update_sets.update(self._parse_update_sets_from_text(story.description))

        # Check comments
        for comment in story.comments:
            update_sets.update(self._parse_update_sets_from_text(comment.body))

        return list(update_sets)

    def _parse_update_sets_from_text(self, text: str) -> List[str]:
        """Parse update set references from text.

        Args:
            text: Text to parse

        Returns:
            List of update set identifiers
        """
        if not text:
            return []

        update_sets = []

        # Pattern 1: ServiceNow URLs with sys_id
        # https://instance.service-now.com/nav_to.do?uri=table/sn_chg_management_update_set.do?sys_id=12345
        pattern1 = r'sys_id=([a-f0-9]{32}|[a-f0-9]{8})'
        matches = re.findall(pattern1, text, re.IGNORECASE)
        update_sets.extend(matches)

        # Pattern 2: Update set names like "us_xxxxx" or "UpdateSet-xxxxx"
        pattern2 = r'(?:us|update_?set)[_-]([a-zA-Z0-9_]+)'
        matches = re.findall(pattern2, text, re.IGNORECASE)
        update_sets.extend([f"us_{m}" for m in matches])

        # Pattern 3: Explicit "UpdateSet: xxxxx" or "Update Set Name: xxxxx"
        pattern3 = r'[Uu]pdate[\s-]*[Ss]et[\s:]+(\S+)'
        matches = re.findall(pattern3, text)
        update_sets.extend(matches)

        # Pattern 4: Direct sys_id references
        pattern4 = r'(?:sys_id|ID)[\s:]+([a-f0-9]{32})'
        matches = re.findall(pattern4, text, re.IGNORECASE)
        update_sets.extend(matches)

        # Remove duplicates and empty values
        update_sets = list(set(s.strip() for s in update_sets if s and s.strip()))
        return update_sets

    def get_current_sprint(self) -> Optional[str]:
        """Get the name of the current active sprint.

        Returns:
            Sprint name or None
        """
        try:
            response = self._make_request(
                'GET',
                f'/rest/agile/1.0/board/{self.config.board_id}/sprint',
                params={'state': 'active'}
            )

            sprints = response.get('values', [])
            if sprints:
                sprint_name = sprints[0].get('name', 'Unknown Sprint')
                self.logger.info(f"Current sprint: {sprint_name}")
                return sprint_name
            return None
        except Exception as e:
            self.logger.warning(f"Failed to get current sprint: {e}")
            return None

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
