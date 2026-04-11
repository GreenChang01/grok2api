from app.dataplane.reverse.protocol.tool_prompt import inject_into_message


def test_inject_into_message_adds_required_suffix():
    out = inject_into_message("hello", "system rules", "required")
    assert "[system]: system rules" in out
    assert "[user]: Return ONLY a <tool_calls> XML block." in out


def test_inject_into_message_adds_forced_tool_suffix():
    out = inject_into_message(
        "hello",
        "system rules",
        {"type": "function", "function": {"name": "query_order_status"}},
    )
    assert 'calling "query_order_status"' in out


def test_inject_into_message_keeps_auto_unchanged():
    out = inject_into_message("hello", "system rules", "auto")
    assert out == "[system]: system rules\n\nhello"
