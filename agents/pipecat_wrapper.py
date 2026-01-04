"""
Here you will find the wrapper to make the langchain create agent work with pipecat.
"""

from .conversation import _raw_agent, CONVERSATIONAL_MODEL

# Wrapper function for Pipecat compatibility
async def _astream(input_dict, config=None):
    """Translates Pipecat format to agent format and streams response."""
    text = input_dict.get("input", "")
    messages = {"messages": [{"role": "user", "content": text}]}

    # Add thread_id for InMemorySaver
    run_config = {"configurable": {"thread_id": "voice-session"}}

    async for chunk in _raw_agent.astream(messages, config=run_config):
        # Handle nested structure: {'model': {'messages': [AIMessage(...)]}}
        if "model" in chunk and "messages" in chunk["model"]:
            for msg in chunk["model"]["messages"]:
                if hasattr(msg, "content") and msg.content:
                    yield msg.content


# Export wrapper that Pipecat can use
class conversation_agent:
    model = CONVERSATIONAL_MODEL
    astream = staticmethod(_astream)