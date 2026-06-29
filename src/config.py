"""Configuration management for the agent."""

import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Load environment variables
load_dotenv()


class JiraConfig(BaseModel):
    """Jira configuration settings."""
    base_url: str = Field(default_factory=lambda: os.getenv("JIRA_BASE_URL", ""))
    username: str = Field(default_factory=lambda: os.getenv("JIRA_USERNAME", ""))
    api_token: str = Field(default_factory=lambda: os.getenv("JIRA_API_TOKEN", ""))
    project_key: str = Field(default_factory=lambda: os.getenv("JIRA_PROJECT_KEY", ""))
    board_id: str = Field(default_factory=lambda: os.getenv("JIRA_BOARD_ID", "1"))
    story_status: str = Field(default_factory=lambda: os.getenv("JIRA_STORY_STATUS", "Ready for Deployment"))

    @validator('base_url', 'username', 'api_token', 'project_key')
    def validate_required(cls, v):
        if not v:
            raise ValueError('This field is required')
        return v

    class Config:
        env_prefix = "JIRA_"


class ServiceNowConfig(BaseModel):
    """ServiceNow configuration settings."""
    instance_url: str = Field(default_factory=lambda: os.getenv("SN_INSTANCE_URL", ""))
    username: str = Field(default_factory=lambda: os.getenv("SN_USERNAME", ""))
    password: str = Field(default_factory=lambda: os.getenv("SN_PASSWORD", ""))
    table: str = Field(default_factory=lambda: os.getenv("SN_TABLE", "sn_chg_management_update_set"))

    @validator('instance_url', 'username', 'password')
    def validate_required(cls, v):
        if not v:
            raise ValueError('This field is required')
        return v

    class Config:
        env_prefix = "SN_"


class SlackConfig(BaseModel):
    """Slack configuration settings."""
    webhook_url: str = Field(default_factory=lambda: os.getenv("SLACK_WEBHOOK_URL", ""))

    @validator('webhook_url')
    def validate_webhook(cls, v):
        if not v:
            raise ValueError('Slack webhook URL is required')
        if not v.startswith('https://'):
            raise ValueError('Slack webhook must be HTTPS')
        return v

    class Config:
        env_prefix = "SLACK_"


class ConfluenceConfig(BaseModel):
    """Confluence configuration settings."""
    enabled: bool = Field(default_factory=lambda: os.getenv("CONFLUENCE_ENABLED", "False").lower() == "true")
    base_url: str = Field(default_factory=lambda: os.getenv("CONFLUENCE_BASE_URL", ""))
    email: str = Field(default_factory=lambda: os.getenv("CONFLUENCE_EMAIL", ""))
    api_token: str = Field(default_factory=lambda: os.getenv("CONFLUENCE_API_TOKEN", ""))
    space_key: str = Field(default_factory=lambda: os.getenv("CONFLUENCE_SPACE_KEY", ""))
    parent_page_id: str = Field(default_factory=lambda: os.getenv("CONFLUENCE_PARENT_PAGE_ID", ""))

    @validator('base_url')
    def validate_base_url(cls, v):
        if v and not v.startswith('https://'):
            raise ValueError('Confluence base URL must be HTTPS')
        return v

    class Config:
        env_prefix = "CONFLUENCE_"


class AgentConfig(BaseModel):
    """Agent configuration settings."""
    name: str = Field(default_factory=lambda: os.getenv("AGENT_NAME", "Jira-ServiceNow Deployment Agent"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    run_on_thursday: bool = Field(default_factory=lambda: os.getenv("RUN_ON_THURSDAY", "True").lower() == "true")
    run_time: str = Field(default_factory=lambda: os.getenv("RUN_TIME", "09:00"))
    dry_run: bool = Field(default_factory=lambda: os.getenv("DRY_RUN", "False").lower() == "true")
    state_file_path: str = Field(default_factory=lambda: os.getenv("STATE_FILE_PATH", "./state/agent_state.json"))
    log_file_path: str = Field(default_factory=lambda: os.getenv("LOG_FILE_PATH", "./logs/agent.log"))

    class Config:
        env_prefix = "AGENT_"


class AppConfig(BaseModel):
    """Complete application configuration."""
    jira: JiraConfig
    servicenow: ServiceNowConfig
    slack: SlackConfig
    confluence: ConfluenceConfig
    agent: AgentConfig

    @staticmethod
    def from_env() -> "AppConfig":
        """Load configuration from environment variables."""
        try:
            return AppConfig(
                jira=JiraConfig(),
                servicenow=ServiceNowConfig(),
                slack=SlackConfig(),
                confluence=ConfluenceConfig(),
                agent=AgentConfig()
            )
        except ValueError as e:
            raise RuntimeError(f"Configuration error: {e}")

    def validate_paths(self):
        """Ensure required directories exist."""
        Path(self.agent.state_file_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.agent.log_file_path).parent.mkdir(parents=True, exist_ok=True)
