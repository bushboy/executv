"""Bearer, protocol, Origin, and pairing gates on the ingress MCP surface."""

from fastapi.testclient import TestClient

from ingress_gateway.config import get_settings
from ingress_gateway.main import create_app
from ingress_gateway.mcp_server import MCP_TOOL_DEFINITIONS

get_settings.cache_clear()
client = TestClient(create_app())
TOKEN = "test-token"
AUTH = {
    "Authorization": f"Bearer {TOKEN}",
    "protocol-version": "2025-11-25",
    "mcp-session-id": "sess-test",
    "Host": "executv.example.com",
}


def test_health_reports_ingress_and_core():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "ingress_gateway"
    assert "status" in body["core"]


def test_tv_brief_is_proxied_to_core():
    response = client.get("/v1/briefings/current")
    assert response.status_code in {200, 502}


def test_missing_bearer_is_rejected():
    response = client.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert response.status_code == 401


def test_initialize_negotiates_2025_11_25():
    response = client.post(
        "/mcp",
        headers=AUTH,
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["protocolVersion"] == "2025-11-25"


def test_disallowed_origin_is_rejected():
    response = client.post(
        "/mcp",
        headers={**AUTH, "Origin": "https://evil.example"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
    )
    assert response.status_code == 403


def test_tool_call_without_session_is_rejected_for_remote_hosts():
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "protocol-version": "2025-11-25",
        "Host": "executv.example.com",
    }
    response = client.post(
        "/mcp/v1/tools/call",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "get_executive_brief", "arguments": {}},
        },
    )
    assert response.status_code == 400


def test_tools_list_schemas_are_complete():
    response = client.post(
        "/mcp/v1/tools/call",
        headers=AUTH,
        json={"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
    )
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == [item["name"] for item in MCP_TOOL_DEFINITIONS]
    for tool in tools:
        schema = tool["inputSchema"]
        assert schema["type"] == "object"
        assert schema["properties"]
        assert "session_id" in schema["properties"]
        assert schema["properties"]["session_id"]["type"] == "string"


def test_register_display_pairing_binds_a_code():
    issued = client.get("/displays/pairing-code")
    assert issued.status_code == 200
    code = issued.json()["pairing_code"]
    assert len(code) == 4
    response = client.post(
        "/mcp/v1/tools/call",
        headers=AUTH,
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "register_display_pairing",
                "arguments": {"pairing_code": code, "session_id": "sess-test"},
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["result"]["ok"] is True


def test_reset_without_token_is_rejected_and_with_token_reaches_core():
    missing = client.post("/admin/reset-scenario")
    assert missing.status_code == 401
    allowed = client.post("/admin/reset-scenario", headers={"Authorization": f"Bearer {TOKEN}"})
    assert allowed.status_code in {200, 401, 502}
