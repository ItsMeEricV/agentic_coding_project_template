# Creating and updating issues in each tracker

The body is the same Markdown everywhere. Only the call changes.

## GitHub (`github <owner/repo>`)

```bash
gh issue create -R <owner/repo> --title '<title>' --body-file - <<'EOF'
<body>
EOF
gh issue edit <n> -R <owner/repo> --body-file - <<'EOF'
<body>
EOF
```

`- [ ]` renders as a task list. The GitHub MCP's `issue_write` works too, if it is connected.

## Linear (`linear <team>`)

Use the Linear MCP's `save_issue` with the team, the title, and `description` set to the Markdown body. The same tool updates an existing issue when given its id. Read the tool's schema for the exact parameter names. Linear stores descriptions as Markdown. If the MCP isn't connected, stop and tell the user. Don't fall back to a raw API token.

## Jira (`jira <project key>`)

Use the Atlassian MCP's `createJiraIssue`, and `editJiraIssue` to update. It takes the project key, the issue type (`Task` unless the user says otherwise), `summary` set to the title, and `description` set to the Markdown body. Parameter names differ between MCP versions, so read the tool's schema first. The MCP converts Markdown for you. Jira's REST v3 API takes only Atlassian Document Format, so don't call it directly. `- [ ]` items may arrive as plain text, which still reads fine. If the MCP isn't connected, stop and tell the user.
