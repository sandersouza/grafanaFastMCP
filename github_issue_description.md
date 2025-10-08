# Bug: search_dashboards tool returns incomplete JSON when using streamable HTTP with ChatGPT/OpenAI

## 🐛 Problem Description

When using the `search_dashboards` tool with streamable HTTP transport alongside ChatGPT/OpenAI, only the first chunk of the JSON response is being read and processed. This results in incomplete dashboard search results being returned to the user.

## 🔍 Root Cause

The issue occurs because:

1. The `search_dashboards` tool currently returns the raw JSON array directly from Grafana's `/search` API endpoint
2. When this array is serialized to JSON and sent via streamable HTTP, it gets chunked into multiple pieces
3. ChatGPT/OpenAI's streaming HTTP client only reads the first chunk and considers the response complete
4. This results in partial/truncated dashboard data being processed

## 🌍 Environment

- **Transport**: Streamable HTTP 
- **Client**: ChatGPT/OpenAI MCP integration
- **Affected Tools**: `search_dashboards` and `search` (both use the same underlying function)

## 📋 Steps to Reproduce

1. Configure the Grafana FastMCP server with streamable HTTP transport
2. Connect to ChatGPT/OpenAI using the MCP integration
3. Use the `search_dashboards` tool with any query that returns multiple dashboards
4. Observe that only partial results are returned (typically just the first dashboard or incomplete data)

## 💡 Expected Behavior

The tool should return complete dashboard search results with all matching dashboards, regardless of the JSON response size.

## 📊 Current vs Expected Response Structure

### Current (Problematic)
```json
[
  {
    "id": 1,
    "uid": "dashboard-1",
    "title": "Dashboard 1",
    ...
  },
  {
    "id": 2,
    "uid": "dashboard-2", 
    "title": "Dashboard 2",
    ...
  }
]
```

### Expected (Fixed)
```json
{
  "dashboards": [
    {
      "id": 1,
      "uid": "dashboard-1",
      "title": "Dashboard 1",
      ...
    },
    {
      "id": 2,
      "uid": "dashboard-2",
      "title": "Dashboard 2", 
      ...
    }
  ],
  "total_count": 2,
  "query": "search_term",
  "type": "dashboard_search_results"
}
```

## 🎯 Proposed Solution

Wrap the raw Grafana API response in a consolidated object structure that:

1. **Prevents JSON chunking issues** by providing a single root object instead of an array
2. **Adds useful metadata** like total count, original query, and response type
3. **Maintains backward compatibility** by preserving original dashboard data in a `dashboards` field
4. **Improves LLM parsing** with a clearer, more structured response format

## 📁 Files Affected

- `app/tools/search.py` - Main search tool implementation
- Function: `_search_dashboards()` - Core search logic
- Tools: `search_dashboards` and `search` - Both user-facing endpoints

## 🏷️ Labels

- `bug`
- `streamable-http`
- `chatgpt-integration`
- `json-chunking`
- `mcp-compatibility`

## 📈 Impact

- **Severity**: High - Affects core functionality when using streamable HTTP with ChatGPT/OpenAI
- **Users Affected**: Anyone using the MCP integration with ChatGPT/OpenAI
- **Workaround**: Use SSE or STDIO transports instead of streamable HTTP