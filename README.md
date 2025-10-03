# Jira MCP Server

A Model Context Protocol (MCP) server that provides seamless integration with Jira instances. This server enables AI applications to interact with Jira issues, projects, and workflows through a standardized interface.

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Client Configuration](#client-configuration)
6. [Available Tools](#available-tools)
7. [Development](#development)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Configuration](#advanced-configuration)
10. [License & Contributing](#license--contributing)

## Features

- **Issue Management**: Search, create, update, and transition Jira issues
- **Issue Linking**: Create links between issues with different relationship types (blocks, relates to, etc.)
- **Project Access**: List and browse Jira projects and components
- **Comments**: Add comments to issues with security levels
- **Time Logging**: Log work time on issues with detailed comments
- **JQL Support**: Full Jira Query Language support for advanced searching
- **Rate Limiting**: Built-in throttling to respect Jira API limits
- **Async Operations**: Fully asynchronous for optimal performance
- **Type Safety**: Pydantic models for structured data validation
- **Multiple Transports**: Support for both STDIO and SSE (HTTP) transports
- **Client Integration**: Works with Claude Code, Gemini CLI, Cursor, and other MCP clients

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/jira-mcp-server.git
cd jira-mcp-server
```

2. Install the package:
```bash
pip install -e .
```

Or install with development dependencies:
```bash
pip install -e ".[dev]"
```

## Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` with your Jira credentials:
```env
JIRA_SERVER_URL=https://your-company.atlassian.net
JIRA_ACCESS_TOKEN=your-personal-access-token
JIRA_VERIFY_SSL=true
JIRA_TIMEOUT=30
JIRA_MAX_RESULTS=100
```

### Jira Cloud Setup

For Jira Cloud (Atlassian Cloud), you'll need to:

1. Create a personal access token:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Use the access token as the JIRA_ACCESS_TOKEN

2. Use your full Atlassian domain (e.g., `https://yourcompany.atlassian.net`)

### Jira Server/Data Center Setup

For on-premise Jira instances:

1. Use your Jira server URL
2. Use your personal access token
3. Ensure the user has appropriate permissions for the operations you need

## Usage

### Running the Server

#### STDIO Transport (Default)

Start the MCP server with STDIO transport (for use with MCP clients):
```bash
jira-mcp-server
```

Or run directly with Python:
```bash
python -m jira_mcp_server.main
```

#### SSE Transport (HTTP)

Start the MCP server with SSE (Server-Sent Events) transport for HTTP-based communication:
```bash
jira-mcp-server --transport sse
```

Or with custom host and port:
```bash
jira-mcp-server --transport sse --host 0.0.0.0 --port 9000
```

Or run directly with Python:
```bash
python -m jira_mcp_server.main --transport sse --host 127.0.0.1 --port 8000
```

When running with SSE transport, the server will expose:
- **SSE Endpoint**: `http://127.0.0.1:8000/sse` (for real-time server-to-client communication)
- **Message Endpoint**: `http://127.0.0.1:8000/messages/` (for client-to-server communication)

#### Transport Types

- **STDIO**: Best for integration with MCP clients like Claude Code, IDEs, or command-line tools
- **SSE**: Best for web applications, REST API integration, or when you need HTTP-based communication

### SSE Client Example

An example SSE client is provided to demonstrate how to connect to the server using HTTP transport:

```bash
# First, start the server with SSE transport
jira-mcp-server --transport sse

# Then run the example client (in another terminal)
python examples/sse_client.py
```

The example client demonstrates:
- Connecting to the SSE endpoint
- Listing available tools
- Getting Jira projects
- Searching for issues

## AI Assistant Prompt Configuration

This repository includes a specialized prompt file (`jira-assistant-prompt.md`) that enhances AI assistants with Jira-specific knowledge and best practices. Copy this prompt to your preferred AI tool's configuration directory for optimal Jira MCP server integration.

### Prompt File Locations

**Claude Code:**
- Copy `jira-assistant-prompt.md` to `CLAUDE.md` in your project root
- Or copy to `~/.claude/CLAUDE.md` for global access

**Gemini CLI:**
- Copy `jira-assistant-prompt.md` to `GEMINI.md` in your project root
- Or copy to `~/.gemini/prompt.md` for global access

**Cursor:**
- After running `make setup-prompts`, copy the contents from either `CLAUDE.md` or `GEMINI.md`
- In Cursor, go to **Preferences > Cursor Settings > Rules & Memories > User Rules**
- Paste the copied content into the User Rules section

### Automated Setup

Use the interactive Makefile to automatically configure prompt files for your organization:

```bash
make setup-prompts
```

This will:
1. **Ask for your Jira project key** (e.g., MYPROJ, DEV, ACME)
2. **Ask for your default assignee email** (your email address)
3. **Optionally set a security level** for your organization (e.g., "Company Employee", "Internal")
4. **Generate customized prompt files**:
   - `CLAUDE.md` (for Claude Code)
   - `GEMINI.md` (for Gemini CLI)

### Manual Setup (Alternative)

If you prefer manual setup:

```bash
# For Claude Code
cp jira-assistant-prompt.md CLAUDE.md

# For Gemini CLI
cp jira-assistant-prompt.md GEMINI.md
```

Then manually edit the files to replace:
- `"PROJ"` → your project key
- `PROJ-` → your project prefix
- `SECURITY_PLACEHOLDER` → your security level
- Default assignee references

### Cleaning Up

To remove generated prompt files:

```bash
make clean
```

## Client Configuration

### Claude Code

Claude Code is Anthropic's code editor application that supports MCP servers for enhanced AI-powered development assistance.

#### Configuration File Locations

Claude Code looks for MCP server configurations in the following locations (in order of precedence):

- **Project-specific**: `.mcp.json` in your project directory
- **Project-specific**: `.claude/settings.json` in your project directory
- **Global**: `~/.mcp.json` in your home directory
- **Global**: `~/.claude/settings.json` in your home directory

**Recommended**: Use a project-specific `.mcp.json` or `.claude/settings.json` file for better portability and team sharing.

#### Setup Steps

1. **Create a project-specific configuration file** (recommended, same format in all options):

```json
{
  "mcpServers": {
    "jira-mcp-server": {
      "command": "python",
      "args": ["-m", "jira_mcp_server.main"],
      "cwd": "/home/user/workspace_git/jira-mcp-server",
    }
  }
}
```

**Option A**: Create `.mcp.json` in your project root:

**Option B**: Create `.claude/settings.json` in your project root:

2. **Or create a global configuration**:

**Option A**: For global access across all projects, create `~/.mcp.json`:


**Option B**: Or create `~/.claude/settings.json`:

3. **Restart Claude Code** to apply the configuration.

4. **Verify the connection** by asking Claude to list your Jira issues or projects.

#### Example Usage

Once connected, you can ask Claude:
- "Show me all my assigned Jira issues"
- "Create a new bug report for the login issue"
- "What are the high priority issues in the PROJECT project?"
- "Add a comment to issue PROJ-123 saying it's been fixed"
- "Log 2 hours of work on issue PROJ-123 for debugging the login bug"
- "Link issue PROJ-123 to PROJ-456 with a 'blocks' relationship"
- "Show me all available link types for this Jira instance"

### Gemini CLI

Gemini CLI is Google's command-line interface that supports MCP servers.

#### Configuration File Locations

- **Global**: `~/.gemini/settings.json`
- **Project-specific**: `<project-root>/.gemini/settings.json`

#### Setup Steps

1. **Create or edit the configuration file**:

```json
{
  "mcpServers": {
    "jira-mcp-server": {
      "command": "python",
      "args": ["-m", "jira_mcp_server.main"],
      "cwd": "/home/user/workspace_git/jira-mcp-server",
      "timeout": 30000,
      "trust": false
    }
  }
}
```

2. **Restart Gemini CLI** to apply the configuration.

3. **Test the connection** by running a command that interacts with Jira.

#### Example Usage

```bash
# Ask about Jira issues
gemini "Show me my assigned Jira issues"

# Create a new issue
gemini "Create a new bug report titled 'Login Error' in project PROJ"

# Log time on an issue
gemini "Log 2 hours on issue PROJ-123 for implementing the new feature"

# Link two issues together
gemini "Link issue PROJ-123 to PROJ-456 with a blocks relationship"
```

### Cursor

Cursor is a code editor that supports MCP servers for AI-powered development assistance.

**Recommended model**: GPT-5 or claude-4-sonnet-1m (MAX)

#### Configuration File Locations

- **Project-specific**: `<project-root>/.cursor/mcp.json`
- **Global**: `~/.cursor/mcp.json`

#### Setup Steps

1. **Create or edit the configuration file**:

```json
{
  "mcpServers": {
    "jira-mcp-server": {
      "command": "python",
      "args": ["-m", "jira_mcp_server.main"],
      "cwd": "/home/user/workspace_git/jira-mcp-server",
    }
  }
}
```

2. **Restart Cursor** to apply the configuration.

3. **Use the integration** by asking Cursor to help with Jira-related tasks in your code.

## Available Tools

The server provides the following MCP tools:

### `search_issues`
Search for issues using JQL (Jira Query Language):
```python
# Example JQL queries:
"project = MYPROJ AND status = Open"
"assignee = currentUser() AND priority = High"
"created >= -7d AND project in (PROJ1, PROJ2)"
```

### `get_issue`
Get detailed information about a specific issue:
```python
get_issue(issue_key="PROJ-123")
```

### `create_issue`
Create a new issue:
```python
create_issue(
    project_key="PROJ",
    summary="Fix login bug",
    description="Users cannot log in with special characters",
    issue_type="Bug",
    priority="High"
)
```

### `update_issue`
Update an existing issue:
```python
update_issue(
    issue_key="PROJ-123",
    summary="Updated summary",
    assignee="john.doe"
)
```

### `transition_issue`
Change the status of an issue:
```python
transition_issue(
    issue_key="PROJ-123",
    transition="Done"
)
```

### `add_comment`
Add a comment to an issue:
```python
add_comment(
    issue_key="PROJ-123",
    comment="This has been resolved"
)
```

### `link_issue`
Create a link between two issues:
```python
link_issue(
    link_type="Blocks",
    inward_issue="PROJ-123",
    outward_issue="PROJ-456",
    comment="This issue blocks the other one"
)
```

### `get_link_types`
Get all available issue link types:
```python
get_link_types()
```

### `log_time`
Log time spent on an issue:
```python
log_time(
    issue_key="PROJ-123",
    time_spent="2h 30m",
    comment="Implemented new feature"
)
```

### `get_projects`
List all accessible projects:
```python
get_projects()
```

### `get_project_components`
Get components for a specific project:
```python
get_project_components(project_key="PROJ")
```

### Available Resources

The server also provides MCP resources for read-only access:

- `jira://issue/{issue_key}` - Get formatted issue details
- `jira://projects` - Get formatted list of all projects

## Development

### Setting up Development Environment

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

3. Format code:
```bash
black jira_mcp_server/
isort jira_mcp_server/
```

4. Type checking:
```bash
mypy jira_mcp_server/
```

### Project Structure

```
jira_mcp_server/
├── __init__.py          # Package initialization
├── config.py            # Configuration management
├── client.py            # Jira client wrapper
├── server.py            # MCP server implementation
└── main.py              # Entry point
```

## Troubleshooting

### Common Issues

#### 1. Connection Failed

**Symptoms**: Client cannot connect to the MCP server

**Solutions**:
- Verify the server is running: `python -m jira_mcp_server.main`
- Check the configuration file paths and syntax
- Ensure Python is in the system PATH
- Verify the working directory (`cwd`) is correct

#### 2. Authentication Errors

**Symptoms**: Server starts but cannot connect to Jira

**Solutions**:
- Verify Jira credentials in the `.env` file
- Check if the Jira server URL is correct
- Ensure the personal access token is valid
- Test credentials with a simple Jira API call

#### 3. Permission Denied

**Symptoms**: Server connects to Jira but cannot perform operations

**Solutions**:
- Check user permissions in Jira
- Verify the user has access to the requested projects
- Ensure the access token has necessary scopes

#### 4. Timeout Issues

**Symptoms**: Requests timeout or hang

**Solutions**:
- Increase the timeout value in configuration
- Check network connectivity to Jira
- Verify Jira server is responsive

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
# Set debug environment variable
export PYTHONPATH=debug

# Run the server with debug output
python -m jira_mcp_server.main
```

### Log Files

Check these locations for error logs:

- **Server logs**: Console output when running the server
- **Client logs**: Check client-specific log directories
- **System logs**: `/var/log/` on Linux/macOS

### Getting Help

If you encounter issues:

1. Check the [Issues](https://github.com/your-username/jira-mcp-server/issues) page
2. Review Jira API documentation
3. Verify your Jira instance configuration
4. Test with a simple MCP client first

## Advanced Configuration

### Custom Environment Variables

You can override any configuration by setting environment variables:

```bash
export JIRA_SERVER_URL="https://custom-jira.company.com"
export JIRA_TIMEOUT="60"
export JIRA_MAX_RESULTS="200"
```

### Multiple Jira Instances

To connect to multiple Jira instances, create separate MCP server configurations:

```json
{
  "mcpServers": {
    "jira-production": {
      "command": "python",
      "args": ["-m", "jira_mcp_server.main"],
      "cwd": "/home/user/workspace_git/jira-mcp-server",
      "env": {
        "JIRA_SERVER_URL": "https://prod.atlassian.net",
        "JIRA_ACCESS_TOKEN": "prod-token"
      }
    },
    "jira-staging": {
      "command": "python",
      "args": ["-m", "jira_mcp_server.main"],
      "cwd": "/home/user/workspace_git/jira-mcp-server",
      "env": {
        "JIRA_SERVER_URL": "https://staging.atlassian.net",
        "JIRA_ACCESS_TOKEN": "staging-token"
      }
    }
  }
}
```

### Security Considerations

- Store credentials securely (use environment variables or secure credential stores)
- Use personal access tokens instead of passwords
- Regularly rotate access tokens
- Limit token permissions to necessary scopes only
- Consider using different tokens for different environments

## License & Contributing

### License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Support

For issues and questions:
- Check the [Issues](https://github.com/jpacker/jira-mcp-server/issues) page
- Review Jira API documentation
- Check MCP specification at https://modelcontextprotocol.io/

---

This guide provides comprehensive instructions for using the Jira MCP server with various clients. The server enables powerful AI-driven interactions with your Jira instance, making it easier to manage issues, projects, and workflows through natural language commands.