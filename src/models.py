"""Data models for Jira stories and ServiceNow update sets."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class JiraComment(BaseModel):
    """Jira story comment model."""
    id: str
    author: Optional[str] = None
    body: str
    created: datetime
    updated: datetime

    class Config:
        arbitrary_types_allowed = True


class JiraStory(BaseModel):
    """Jira story model."""
    key: str
    summary: str
    description: Optional[str] = None
    status: str
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    labels: List[str] = Field(default_factory=list)
    created: datetime
    updated: datetime
    comments: List[JiraComment] = Field(default_factory=list)
    update_set_links: List[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class UpdateSet(BaseModel):
    """ServiceNow update set model."""
    name: str
    description: Optional[str] = None
    parent_update_set: Optional[str] = None
    status: str = "in_progress"
    jira_story_key: Optional[str] = None
    jira_story_summary: Optional[str] = None
    type: str = "regular"  # regular, parent, child
    is_complete: bool = False
    created_on: Optional[datetime] = None
    updated_on: Optional[datetime] = None
    sys_id: Optional[str] = None  # ServiceNow system ID
    custom_fields: dict = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class StoryUpdateSetMapping(BaseModel):
    """Mapping of Jira story to update sets."""
    story_key: str
    story_summary: str
    assignee: Optional[str] = None
    update_sets: List[str] = Field(default_factory=list)
    parent_sys_id: Optional[str] = None


class SyncResult(BaseModel):
    """Result of a sync operation."""
    success: bool = False
    total_stories: int = 0
    synced_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    story_mappings: List[StoryUpdateSetMapping] = Field(default_factory=list)
    parent_update_set_name: Optional[str] = None
    parent_update_set_id: Optional[str] = None
    created_child_update_sets: List[str] = Field(default_factory=list)
    child_update_set_summaries: List[dict] = Field(default_factory=list)
    failed_stories: List[dict] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    sprint_name: Optional[str] = None
    run_date: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class AgentState(BaseModel):
    """Agent state model for persistence."""
    last_sync_time: Optional[datetime] = None
    last_parent_created: Optional[str] = None
    processed_stories: List[str] = Field(default_factory=list)
    created_update_sets: dict = Field(default_factory=dict)  # Maps Jira key to ServiceNow sys_id
    error_count: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0
    last_error: Optional[str] = None
    last_error_time: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True
