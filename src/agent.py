"""Main agent orchestrator for Jira-ServiceNow deployment sync."""

import time
from typing import List, Optional
from datetime import datetime
from src.config import AppConfig
from src.jira_client import JiraClient
from src.servicenow_client import ServiceNowClient
from src.slack_notifier import SlackNotifier
from src.confluence_client import ConfluenceClient
from src.state_manager import StateManager
from src.models import JiraStory, SyncResult, StoryUpdateSetMapping
from src.logger import LoggerMixin, setup_logging
from src.utils import generate_parent_deployment_name, format_duration


class JiraServiceNowDeploymentAgent(LoggerMixin):
    """Main agent for syncing ready-to-deploy Jira stories to ServiceNow update sets."""

    def __init__(self, config: AppConfig):
        """Initialize the agent.

        Args:
            config: Application configuration
        """
        self.config = config
        self.jira_client = JiraClient(config.jira)
        self.servicenow_client = ServiceNowClient(config.servicenow)
        self.slack_notifier = SlackNotifier(config.slack, config.servicenow)
        self.confluence_client = ConfluenceClient(config.confluence)
        self.state_manager = StateManager(config.agent.state_file_path)
        self._logger = setup_logging(config.agent)

    def run(self, dry_run: bool = False) -> SyncResult:
        """Run deployment sync.

        Args:
            dry_run: If True, don't make actual changes

        Returns:
            SyncResult with deployment details
        """
        self.logger.info(f"Starting {self.config.agent.name}")
        if dry_run:
            self.logger.warning("Running in DRY RUN mode - no changes will be made")

        result = SyncResult()
        start_time = datetime.utcnow()

        try:
            # Get current sprint
            sprint_name = self.jira_client.get_current_sprint()
            result.sprint_name = sprint_name
            self.logger.info(f"Current sprint: {sprint_name}")

            # Fetch stories ready for deployment
            stories = self.jira_client.fetch_ready_for_deployment_stories()
            result.total_stories = len(stories)
            self.logger.info(f"Fetched {len(stories)} stories ready for deployment")

            if not stories:
                self.logger.warning("No stories ready for deployment")
                result.success = True
                return self._finalize_result(result, start_time, dry_run)

            # Create parent deployment update set
            parent_name = generate_parent_deployment_name(sprint_name)
            parent_sys_id = self.servicenow_client.create_parent_deployment_set(
                parent_name=parent_name,
                sprint_name=sprint_name,
                dry_run=dry_run
            )

            if not parent_sys_id:
                raise Exception(f"Failed to create parent update set: {parent_name}")

            result.parent_update_set_name = parent_name
            result.parent_update_set_id = parent_sys_id
            self.logger.info(f"Created parent update set | name={parent_name} | sys_id={parent_sys_id}")

            # Process each story and add update sets to parent
            for story in stories:
                if self.state_manager.is_story_processed(story.key):
                    self.logger.info(f"Skipping already processed story | key={story.key}")
                    result.skipped_count += 1
                    continue

                try:
                    self._process_story(story, parent_sys_id, result, dry_run)
                except Exception as e:
                    self.logger.error(f"Error processing story {story.key}: {e}")
                    result.failed_count += 1
                    result.failed_stories.append({
                        'key': story.key,
                        'summary': story.summary,
                        'error': str(e)
                    })

            result.success = result.failed_count == 0
            self.logger.info(
                f"Deployment sync completed | synced={result.synced_count} | "
                f"failed={result.failed_count} | skipped={result.skipped_count}"
            )

        except Exception as e:
            self.logger.error(f"Fatal error during deployment sync: {e}")
            result.success = False
            result.errors.append(str(e))
            self.state_manager.record_sync_failure(str(e))
            self.slack_notifier.send_error_notification(str(e), result.sprint_name)
            return self._finalize_result(result, start_time, dry_run)

        # Update state
        if result.success:
            self.state_manager.record_sync_success()
            self.state_manager.set_last_parent(result.parent_update_set_id)
        else:
            self.state_manager.record_sync_failure(f"{result.failed_count} stories failed")

        if not dry_run and result.parent_update_set_id:
            result.child_update_set_summaries = self.servicenow_client.get_child_update_set_summaries(
                result.parent_update_set_id
            )

        # Publish external reports
        if not dry_run:
            try:
                self.confluence_client.publish_weekly_deployment(result)
            except Exception as e:
                self.logger.error(f"Failed to publish Confluence deployment page: {e}")

            self.slack_notifier.send_deployment_report(result)

        return self._finalize_result(result, start_time, dry_run)

    def _process_story(self, story: JiraStory, parent_sys_id: str, result: SyncResult,
                      dry_run: bool = False):
        """Process a single story and add its update sets to parent.

        Args:
            story: JiraStory object
            parent_sys_id: Parent update set sys_id
            result: SyncResult to update
            dry_run: If True, don't make actual changes
        """
        # Skip if no update sets found
        if not story.update_set_links:
            self.logger.debug(f"Story has no update set links | key={story.key}")
            result.skipped_count += 1
            return

        self.logger.info(
            f"Processing story | key={story.key} | update_sets={len(story.update_set_links)} | "
            f"assignee={story.assignee}"
        )

        # Create mapping entry
        mapping = StoryUpdateSetMapping(
            story_key=story.key,
            story_summary=story.summary,
            assignee=story.assignee,
            update_sets=story.update_set_links,
            parent_sys_id=parent_sys_id
        )

        # Add each update set as child
        successful_children = 0
        for update_set_name in story.update_set_links:
            child_sys_id = self.servicenow_client.create_child_update_set(
                update_set_name=update_set_name,
                parent_sys_id=parent_sys_id,
                jira_story_key=story.key,
                jira_story_summary=story.summary,
                dry_run=dry_run
            )

            if child_sys_id:
                successful_children += 1
                result.created_child_update_sets.append(update_set_name)
                self.state_manager.add_update_set_mapping(story.key, child_sys_id)

        # Mark story as processed if at least some children were created
        if successful_children > 0:
            self.state_manager.mark_story_processed(story.key)
            result.synced_count += 1
            result.story_mappings.append(mapping)
            self.logger.info(
                f"Successfully processed story | key={story.key} | "
                f"update_sets_added={successful_children}"
            )
        else:
            result.failed_count += 1
            result.failed_stories.append({
                'key': story.key,
                'summary': story.summary,
                'error': 'No update sets could be created'
            })

    def _finalize_result(self, result: SyncResult, start_time: datetime,
                        dry_run: bool = False) -> SyncResult:
        """Finalize sync result with timing and summary.

        Args:
            result: SyncResult object
            start_time: Sync start time
            dry_run: If dry run

        Returns:
            Updated SyncResult
        """
        result.completed_at = datetime.utcnow()
        result.duration_seconds = (result.completed_at - start_time).total_seconds()
        result.run_date = result.started_at.strftime('%Y-%m-%d')

        log_message = (
            f"Deployment sync finished | success={result.success} | "
            f"total_stories={result.total_stories} | synced={result.synced_count} | "
            f"failed={result.failed_count} | skipped={result.skipped_count} | "
            f"duration={format_duration(result.duration_seconds)}"
        )

        if dry_run:
            log_message += " [DRY RUN]"

        self.logger.info(log_message)
        return result

    def cleanup(self):
        """Clean up resources."""
        self.jira_client.close()
        self.servicenow_client.close()
        self.confluence_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
