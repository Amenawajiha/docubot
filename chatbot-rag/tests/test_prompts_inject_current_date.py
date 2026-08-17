from datetime import date

from src.llm.prompt_builder import PromptBuilder


def test_system_prompt_includes_current_date():
    builder = PromptBuilder()
    messages = builder.build_user_conversation_messages("Hello")
    assert isinstance(messages, list)
    assert messages[0]["role"] == "system"
    system_content = messages[0]["content"]
    today = date.today().isoformat()
    assert today in system_content, f"Expected current date {today} in system prompt" 
