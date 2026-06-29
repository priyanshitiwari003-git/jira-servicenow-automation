"""Tests for the main agent."""

import pytest
from unittest.mock import patch, MagicMock
from src.agent import JiraServiceNowDeploymentAgent
from src.config import AppConfig, JiraConfig, ServiceNowConfig, SlackConfig, AgentConfig


@pytest.fixture
def app_config():
    """Create test app config."""
    return AppConfig(
        jira=JiraConfig(
            base_url='https://test.atlassian.net',
            username='test@example.com',
            api_token='test-token',
            project_key='TEST',
            board_id='1'
        ),
        servicenow=ServiceNowConfig(
            instance_url='https://test.service-now.com',
            username='testuser',
            password='testpass',
            table='sn_chg_management_update_set'
        ),
        slack=SlackConfig(
            webhook_url='https://example.com/webhook'
        ),
        agent=AgentConfig(
            name='Test Agent',
            log_level='DEBUG',
            run_on_thursday=True,
            run_time='09:00',
            dry_run=False,
            state_file_path='/tmp/test_state.json',
            log_file_path='/tmp/test.log'
        )
    )


@patch('src.agent.JiraClient')
@patch('src.agent.ServiceNowClient')
@patch('src.agent.StateManager')
def test_agent_init(mock_state_manager, mock_sn_client, mock_jira_client, app_config):
    """Test agent initialization."""
    agent = JiraServiceNowDeploymentAgent(app_config)

    assert agent.config == app_config


@patch('src.agent.JiraClient')
@patch('src.agent.ServiceNowClient')
@patch('src.agent.StateManager')
def test_run_no_stories(mock_state_manager, mock_sn_client, mock_jira_client, app_config):
    """Test running once with no stories."""
    mock_jira_instance = MagicMock()
    mock_jira_instance.get_current_sprint.return_value = None
    mock_jira_instance.fetch_ready_for_deployment_stories.return_value = []
    mock_jira_client.return_value = mock_jira_instance

    agent = JiraServiceNowDeploymentAgent(app_config)
    result = agent.run(dry_run=True)

    assert result.success
    assert result.total_stories == 0
