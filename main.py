#!/usr/bin/env python3
"""Entry point for the Jira-ServiceNow Deployment Agent."""

import sys
import time
import click
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from src.config import AppConfig
from src.agent import JiraServiceNowDeploymentAgent
from src.logger import setup_logging
from src.utils import is_thursday, is_time_within_window


@click.command()
@click.option('--run', is_flag=True, help='Run deployment sync now')
@click.option('--schedule', is_flag=True, help='Run on schedule (Thursdays at specified time)')
@click.option('--dry-run', is_flag=True, help='Preview changes without making them')
@click.option('--reset-state', is_flag=True, help='Reset agent state')
def main(run: bool, schedule: bool, dry_run: bool, reset_state: bool):
    """Jira-ServiceNow Deployment Agent.

    Fetches stories in 'Ready for Deployment' status from Jira,
    extracts update set links from comments, and creates a parent
    deployment update set in ServiceNow with all update sets as children.
    """
    try:
        # Load configuration
        config = AppConfig.from_env()
        config.validate_paths()
        logger = setup_logging(config.agent)

        logger.info(f"Initializing {config.agent.name}")
        logger.info(f"Jira: {config.jira.base_url} | Project: {config.jira.project_key}")
        logger.info(f"ServiceNow: {config.servicenow.instance_url}")
        logger.info(f"Slack Webhook: {'Configured' if config.slack.webhook_url else 'Not configured'}")
        logger.info(f"Confluence: {'Configured' if config.confluence.enabled else 'Disabled'}")

        # Initialize agent
        agent = JiraServiceNowDeploymentAgent(config)

        # Handle state reset
        if reset_state:
            logger.warning("Resetting agent state")
            agent.state_manager.reset()
            logger.info("State reset complete")
            return

        # Show current state
        logger.info(agent.state_manager.get_summary())

        # Run now
        if run or (not schedule and not reset_state):
            logger.info("Running deployment sync now")
            result = agent.run(dry_run=dry_run)
            logger.info(f"Result: success={result.success}, synced={result.synced_count}, failed={result.failed_count}")
            agent.cleanup()
            sys.exit(0 if result.success else 1)

        # Schedule for Thursdays
        if schedule:
            _run_scheduled(agent, config, logger, dry_run)

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def _run_scheduled(agent, config, logger, dry_run: bool):
    """Run agent on schedule.

    Args:
        agent: JiraServiceNowDeploymentAgent instance
        config: AppConfig
        logger: Logger instance
        dry_run: If True, don't make actual changes
    """
    scheduler = BackgroundScheduler()

    def scheduled_job():
        logger.info("Scheduled deployment sync started")
        try:
            result = agent.run(dry_run=dry_run)
            logger.info(f"Scheduled sync completed | success={result.success}")
        except Exception as e:
            logger.error(f"Error in scheduled sync: {e}")

    # Parse run time
    try:
        hour, minute = map(int, config.agent.run_time.split(':'))
    except (ValueError, IndexError):
        logger.error(f"Invalid RUN_TIME format: {config.agent.run_time}. Expected HH:MM")
        sys.exit(1)

    if config.agent.run_on_thursday:
        # Schedule for Thursday
        logger.info(f"Agent scheduled for Thursday at {config.agent.run_time}")
        scheduler.add_job(
            scheduled_job,
            'cron',
            day_of_week=3,  # Thursday
            hour=hour,
            minute=minute,
            id='thursday_deployment_sync'
        )
    else:
        # Schedule daily
        logger.info(f"Agent scheduled daily at {config.agent.run_time}")
        scheduler.add_job(
            scheduled_job,
            'cron',
            hour=hour,
            minute=minute,
            id='daily_deployment_sync'
        )

    scheduler.start()
    logger.info("Scheduler started. Press Ctrl+C to exit.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        scheduler.shutdown()
        agent.cleanup()
        sys.exit(0)


if __name__ == '__main__':
    main()
