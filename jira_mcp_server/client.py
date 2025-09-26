"""Jira client wrapper for MCP server."""

import asyncio
from typing import List, Dict, Any, Optional
from jira import JIRA
from jira.exceptions import JIRAError
from asyncio_throttle import Throttler

from .config import JiraConfig


class JiraClient:
    """Async wrapper for Jira client with rate limiting."""
    
    def __init__(self, config: JiraConfig):
        """Initialize Jira client with configuration."""
        self.config = config
        self._jira: Optional[JIRA] = None
        self.throttler = Throttler(rate_limit=10, period=1.0)  # 10 requests per second
    
    async def connect(self) -> None:
        """Connect to Jira server using personal access token authentication."""
        try:
            self._jira = JIRA(
                server=self.config.server_url,
                token_auth=self.config.access_token,
                options={
                    'verify': self.config.verify_ssl,
                    'timeout': self.config.timeout
                }
            )
            # Test connection
            await self._async_call(lambda: self._jira.myself())
        except JIRAError as e:
            raise ConnectionError(f"Failed to connect to Jira: {e}")
    
    async def _async_call(self, func):
        """Execute synchronous Jira calls asynchronously with throttling."""
        async with self.throttler:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, func)
    
    async def search_issues(self, jql: str, max_results: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search for issues using JQL."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        max_results = max_results or self.config.max_results
        
        try:
            issues = await self._async_call(
                lambda: self._jira.search_issues(
                    jql,
                    maxResults=max_results,
                    expand='changelog'
                )
            )
            
            return [self._issue_to_dict(issue) for issue in issues]
        except JIRAError as e:
            raise ValueError(f"JQL search failed: {e}")
    
    async def get_issue(self, issue_key: str) -> Dict[str, Any]:
        """Get a specific issue by key."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(
                lambda: self._jira.issue(
                    issue_key,
                    expand='changelog,transitions,comments'
                )
            )
            return self._issue_to_dict(issue)
        except JIRAError as e:
            raise ValueError(f"Failed to get issue {issue_key}: {e}")
    
    async def create_issue(self, project_key: str, summary: str, description: str, 
                          issue_type: str = "Task", **fields) -> Dict[str, Any]:
        """Create a new issue."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        # Convert timetracking.originalEstimate from time string to minutes for Jira API
        if 'timetracking' in fields and isinstance(fields['timetracking'], dict):
            if 'originalEstimate' in fields['timetracking'] and isinstance(fields['timetracking']['originalEstimate'], str):
                seconds = self._time_string_to_seconds(fields['timetracking']['originalEstimate'])
                fields['timetracking']['originalEstimate'] = str(seconds // 60)  # Jira expects minutes as string
        
        issue_dict = {
            'project': {'key': project_key},
            'summary': summary,
            'description': description,
            'issuetype': {'name': issue_type},
            **fields
        }
        
        try:
            issue = await self._async_call(
                lambda: self._jira.create_issue(fields=issue_dict)
            )
            return self._issue_to_dict(issue)
        except JIRAError as e:
            raise ValueError(f"Failed to create issue: {e}")
    
    async def update_issue(self, issue_key: str, **fields) -> Dict[str, Any]:
        """Update an existing issue."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        # Convert timetracking.originalEstimate from time string to minutes for Jira API
        if 'timetracking' in fields and isinstance(fields['timetracking'], dict):
            if 'originalEstimate' in fields['timetracking'] and isinstance(fields['timetracking']['originalEstimate'], str):
                seconds = self._time_string_to_seconds(fields['timetracking']['originalEstimate'])
                fields['timetracking']['originalEstimate'] = str(seconds // 60)  # Jira expects minutes as string
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            await self._async_call(lambda: issue.update(fields=fields))
            # Return updated issue
            return await self.get_issue(issue_key)
        except JIRAError as e:
            raise ValueError(f"Failed to update issue {issue_key}: {e}")
    
    async def transition_issue(self, issue_key: str, transition: str) -> Dict[str, Any]:
        """Transition an issue to a new status."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            transitions = await self._async_call(lambda: self._jira.transitions(issue))
            
            # Find transition by name
            transition_id = None
            for t in transitions:
                if t['name'].lower() == transition.lower():
                    transition_id = t['id']
                    break
            
            if not transition_id:
                available = [t['name'] for t in transitions]
                raise ValueError(f"Transition '{transition}' not available. Available: {available}")
            
            await self._async_call(
                lambda: self._jira.transition_issue(issue, transition_id)
            )
            
            return await self.get_issue(issue_key)
        except JIRAError as e:
            raise ValueError(f"Failed to transition issue {issue_key}: {e}")
    
    async def add_comment(self, issue_key: str, comment: str, security_level: Optional[str] = None) -> Dict[str, Any]:
        """Add a comment to an issue."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))

            # Build comment parameters
            comment_kwargs = {}
            if security_level:
                # Use 'group' type for security levels like "Red Hat Employee"
                comment_kwargs['visibility'] = {'type': 'group', 'value': security_level}

            comment_obj = await self._async_call(
                lambda: self._jira.add_comment(issue, comment, **comment_kwargs)
            )
            
            return {
                'id': comment_obj.id,
                'body': comment_obj.body,
                'author': comment_obj.author.displayName,
                'created': comment_obj.created,
                'updated': comment_obj.updated
            }
        except JIRAError as e:
            raise ValueError(f"Failed to add comment to {issue_key}: {e}")
    
    async def log_work(self, issue_key: str, time_spent: str, comment: str, started: Optional[str] = None) -> Dict[str, Any]:
        """Log work time on an issue with a comment."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(lambda: self._jira.issue(issue_key))
            
            # Prepare work log parameters
            work_log_params = {
                'timeSpent': time_spent,
                'comment': comment
            }
            
            # Add started time if provided
            if started:
                work_log_params['started'] = started
            
            # Log the work using direct parameters instead of a dictionary
            work_log_obj = await self._async_call(
                lambda: self._jira.add_worklog(issue, **work_log_params)
            )
            
            return {
                'id': work_log_obj.id,
                'time_spent': work_log_obj.timeSpent,
                'comment': work_log_obj.comment,
                'author': work_log_obj.author.displayName,
                'created': work_log_obj.created,
                'started': work_log_obj.started
            }
        except JIRAError as e:
            raise ValueError(f"Failed to log work on {issue_key}: {e}")
    
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            projects = await self._async_call(lambda: self._jira.projects())
            return [
                {
                    'key': project.key,
                    'name': project.name,
                    'description': getattr(project, 'description', ''),
                    'lead': getattr(project.lead, 'displayName', '') if hasattr(project, 'lead') else ''
                }
                for project in projects
            ]
        except JIRAError as e:
            raise ValueError(f"Failed to get projects: {e}")

    async def get_project_components(self, project_key: str) -> List[Dict[str, Any]]:
        """Get all components for a specific project."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")

        try:
            components = await self._async_call(
                lambda: self._jira.project_components(project_key)
            )
            return [
                {
                    'id': component.id,
                    'name': component.name,
                    'description': getattr(component, 'description', '') or '',
                    'lead': getattr(component.lead, 'displayName', '') if getattr(component, 'lead', None) else '',
                    'assignee_type': getattr(component, 'assigneeType', ''),
                    'is_assignee_type_valid': getattr(component, 'isAssigneeTypeValid', False)
                }
                for component in components
            ]
        except JIRAError as e:
            raise ValueError(f"Failed to get components for project {project_key}: {e}")
    
    async def create_issue_link(
        self, 
        link_type: str, 
        inward_issue: str, 
        outward_issue: str, 
        comment: Optional[str] = None,
        security_level: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a link between two issues.
        
        Args:
            link_type: The type of link to create (e.g., 'Blocks', 'Relates', 'Duplicates')
            inward_issue: The issue key to link from (e.g., 'PROJ-123')
            outward_issue: The issue key to link to (e.g., 'PROJ-456')
            comment: Optional comment to add when creating the link
            security_level: Optional security level for the comment
            
        Returns:
            Dict containing link information
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            # Prepare comment data if provided
            comment_data = None
            if comment:
                comment_data = {'body': comment}
                if security_level:
                    comment_data['visibility'] = {'type': 'group', 'value': security_level}
            
            # Create the issue link
            response = await self._async_call(
                lambda: self._jira.create_issue_link(
                    type=link_type,
                    inwardIssue=inward_issue,
                    outwardIssue=outward_issue,
                    comment=comment_data
                )
            )
            
            # Get link types to find the proper names
            link_types = await self._async_call(lambda: self._jira.issue_link_types())
            link_type_info = None
            for lt in link_types:
                if lt.name.lower() == link_type.lower():
                    link_type_info = lt
                    break
            
            return {
                'link_type': link_type,
                'inward_issue': inward_issue,
                'outward_issue': outward_issue,
                'inward_description': link_type_info.inward if link_type_info else None,
                'outward_description': link_type_info.outward if link_type_info else None,
                'comment': comment,
                'created': True
            }
            
        except JIRAError as e:
            raise ValueError(f"Failed to create issue link: {e}")
    
    async def get_issue_link_types(self) -> List[Dict[str, Any]]:
        """Get available issue link types.
        
        Returns:
            List of available link types with their descriptions
        """
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            link_types = await self._async_call(lambda: self._jira.issue_link_types())
            return [
                {
                    'id': lt.id,
                    'name': lt.name,
                    'inward': lt.inward,
                    'outward': lt.outward
                }
                for lt in link_types
            ]
        except JIRAError as e:
            raise ValueError(f"Failed to get issue link types: {e}")

    async def get_raw_issue_fields(self, issue_key: str) -> Dict[str, Any]:
        """Get all raw fields from a Jira issue for debugging purposes."""
        if not self._jira:
            raise RuntimeError("Not connected to Jira")
        
        try:
            issue = await self._async_call(
                lambda: self._jira.issue(
                    issue_key,
                    expand='changelog,transitions,comments'
                )
            )
            
            # Convert the raw issue fields to a dictionary
            raw_fields = {}
            
            # Get all field attributes
            for field_name in dir(issue.fields):
                if not field_name.startswith('_'):
                    try:
                        field_value = getattr(issue.fields, field_name)
                        if field_value is not None:
                            # Try to serialize the field value
                            if hasattr(field_value, '__dict__'):
                                # Complex object, get its attributes
                                if hasattr(field_value, 'name'):
                                    raw_fields[field_name] = field_value.name
                                elif hasattr(field_value, 'value'):
                                    raw_fields[field_name] = field_value.value
                                else:
                                    raw_fields[field_name] = str(field_value)
                            elif isinstance(field_value, list):
                                # Handle lists
                                raw_fields[field_name] = [
                                    item.name if hasattr(item, 'name') else str(item) 
                                    for item in field_value
                                ]
                            else:
                                # Simple value
                                raw_fields[field_name] = field_value
                    except Exception as e:
                        # If we can't access a field, note the error
                        raw_fields[field_name] = f"Error accessing field: {str(e)}"
            
            # Add some metadata
            result = {
                'issue_key': issue.key,
                'raw_fields': raw_fields,
                'field_count': len(raw_fields)
            }
            
            return result
            
        except JIRAError as e:
            raise ValueError(f"Failed to get raw fields for issue {issue_key}: {e}")
    
    def _extract_custom_field_value(self, field_value):
        """Extract string value from custom field that might be a CustomFieldOption object."""
        if field_value is None:
            return None
        
        # Debug: log the type for troubleshooting
        field_type = type(field_value).__name__
        
        # Handle CustomFieldOption objects from Jira library
        if hasattr(field_value, 'value'):
            return str(field_value.value)
        # Handle dict-like objects that might have a 'value' key
        if isinstance(field_value, dict) and 'value' in field_value:
            return str(field_value['value'])
        # Handle string values directly
        if isinstance(field_value, str):
            return field_value
        # Handle objects with name attribute (common in Jira)
        if hasattr(field_value, 'name'):
            return str(field_value.name)
        
        # For CustomFieldOption specifically, try to access its string representation or properties
        if 'CustomFieldOption' in field_type:
            # Try various common attributes
            for attr in ['value', 'name', 'displayName', 'id']:
                if hasattr(field_value, attr):
                    val = getattr(field_value, attr)
                    if val is not None:
                        return str(val)
        
        # Fallback to string conversion
        return str(field_value)
    
    def _extract_git_pull_requests(self, field_value):
        """Extract git pull requests from custom field that might be a list or string."""
        if field_value is None:
            return None
        
        # If it's already a string, return it
        if isinstance(field_value, str):
            return field_value
        
        # If it's a list, join the items with commas
        if isinstance(field_value, list):
            # Filter out None values and convert all items to strings
            valid_items = [str(item) for item in field_value if item is not None]
            return ', '.join(valid_items) if valid_items else None
        
        # Fallback to string conversion
        return str(field_value)
    
    def _time_string_to_seconds(self, time_string: str) -> int:
        """Convert Jira time format (e.g., '1h 30m', '2d', '45m') to seconds."""
        if not time_string:
            return None
        
        # Remove whitespace and convert to lowercase
        time_string = time_string.replace(' ', '').lower()
        
        total_seconds = 0
        current_number = ''
        
        for char in time_string:
            if char.isdigit() or char == '.':
                current_number += char
            elif char in ['d', 'h', 'm', 's']:
                if current_number:
                    value = float(current_number)
                    if char == 'd':  # days
                        total_seconds += value * 24 * 3600
                    elif char == 'h':  # hours
                        total_seconds += value * 3600
                    elif char == 'm':  # minutes
                        total_seconds += value * 60
                    elif char == 's':  # seconds
                        total_seconds += value
                    current_number = ''
        
        return int(total_seconds)
    
    def _seconds_to_time_string(self, seconds: int) -> str:
        """Convert seconds to Jira time format (e.g., '1h 30m')."""
        if seconds is None:
            return None
        
        # Convert to days, hours, minutes
        days = seconds // (24 * 3600)
        remaining_seconds = seconds % (24 * 3600)
        hours = remaining_seconds // 3600
        minutes = (remaining_seconds % 3600) // 60
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        
        if not parts:
            return "0m"
        
        return " ".join(parts)
    
    def _issue_to_dict(self, issue) -> Dict[str, Any]:
        """Convert Jira issue object to dictionary."""
        result = {
            'key': issue.key,
            'summary': issue.fields.summary,
            'description': getattr(issue.fields, 'description', '') or '',
            'status': issue.fields.status.name,
            'priority': getattr(issue.fields.priority, 'name', '') if issue.fields.priority else '',
            'issue_type': issue.fields.issuetype.name,
            'project': issue.fields.project.key,
            'assignee': issue.fields.assignee.displayName if issue.fields.assignee else None,
            'reporter': issue.fields.reporter.displayName if issue.fields.reporter else None,
            'created': issue.fields.created,
            'updated': issue.fields.updated,
            'resolution': issue.fields.resolution.name if issue.fields.resolution else None,
            'labels': getattr(issue.fields, 'labels', []),
            'components': [comp.name for comp in getattr(issue.fields, 'components', [])],
            'comments': [
                {
                    'id': comment.id,
                    'body': comment.body,
                    'author': comment.author.displayName,
                    'created': comment.created,
                    'updated': comment.updated
                }
                for comment in getattr(getattr(issue.fields, 'comment', None), 'comments', []) or []
            ],
            'url': f"{self.config.server_url}/browse/{issue.key}",
            'fix_versions': [version.name for version in getattr(issue.fields, 'fixVersions', [])],
            'work_type': self._extract_custom_field_value(getattr(issue.fields, 'customfield_12320040', None)),  # Work type custom field
            'security_level': getattr(issue.fields.security, 'name', None) if getattr(issue.fields, 'security', None) else None,
            'due_date': getattr(issue.fields, 'duedate', None),
            'target_start': getattr(issue.fields, 'customfield_12313941', None),  # Target Start custom field
            'target_end': getattr(issue.fields, 'customfield_12313942', None),  # Target End custom field
            'original_estimate': self._seconds_to_time_string(getattr(issue.fields, 'timeoriginalestimate', None)),
            'story_points': getattr(issue.fields, 'customfield_12310243', None),  # Story points custom field
            'git_commit': self._extract_custom_field_value(getattr(issue.fields, 'customfield_12317372', None)),  # Git Commit custom field
            'git_pull_requests': self._extract_git_pull_requests(getattr(issue.fields, 'customfield_12310220', None)),  # Git Pull Requests custom field
            'subtasks': [
                {
                    'key': subtask.key,
                    'summary': subtask.fields.summary,
                    'status': subtask.fields.status.name,
                    'issue_type': subtask.fields.issuetype.name
                }
                for subtask in getattr(issue.fields, 'subtasks', [])
            ],
            'parent': {
                'key': issue.fields.parent.key,
                'summary': issue.fields.parent.fields.summary,
                'issue_type': issue.fields.parent.fields.issuetype.name
            } if getattr(issue.fields, 'parent', None) else None
        }

        # Add Epic Link field when issue type is Story
        if issue.fields.issuetype.name == 'Story':
            epic_link = getattr(issue.fields, 'customfield_12311140', None)
            result['epic_link'] = epic_link

        return result