"""Tests for ServiceNow client."""

import pytest
from unittest.mock import MagicMock, patch
from src.servicenow_client import ServiceNowClient
from src.config import ServiceNowConfig
from src.models import UpdateSet


@pytest.fixture
def sn_config():
    """Create test ServiceNow config."""
    return ServiceNowConfig(
        instance_url='https://test.service-now.com',
        username='testuser',
        password='testpass',
        table='sn_chg_management_update_set'
    )


@pytest.fixture
def sn_client(sn_config):
    """Create test ServiceNow client."""
    return ServiceNowClient(sn_config)


def test_servicenow_client_init(sn_client):
    """Test ServiceNow client initialization."""
    assert sn_client.instance_url == 'https://test.service-now.com'
    assert sn_client.table == 'sn_chg_management_update_set'


@patch('requests.Session.request')
def test_create_parent_update_set(mock_request, sn_client):
    """Test creating a parent deployment update set."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'result': {
            'sys_id': '12345',
            'name': 'parent_test'
        }
    }
    mock_request.return_value = mock_response

    sys_id = sn_client.create_parent_deployment_set(
        parent_name='parent_test',
        sprint_name='Sprint 1',
        dry_run=False
    )

    assert sys_id == '12345'


@patch('requests.Session.request')
def test_create_child_update_set(mock_request, sn_client):
    """Test creating a child update set."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'result': {
            'sys_id': '67890',
            'name': 'child_test'
        }
    }
    mock_request.return_value = mock_response

    sys_id = sn_client.create_child_update_set(
        update_set_name='child_test',
        parent_sys_id='12345',
        jira_story_key='TEST-1',
        jira_story_summary='Test story',
        dry_run=False
    )

    assert sys_id == '67890'


def test_create_update_set_dry_run(sn_client):
    """Test creating update set in dry run mode."""
    sys_id = sn_client.create_child_update_set(
        update_set_name='test_update_set',
        parent_sys_id='parent123',
        jira_story_key='TEST-1',
        jira_story_summary='Test',
        dry_run=True
    )

    assert sys_id == 'dry_run_test_update_set'
