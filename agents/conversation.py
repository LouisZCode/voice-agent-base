from dotenv import load_dotenv
from langchain.agents import create_agent
from .load_prompts import load_prompts
from langgraph.checkpoint.memory import InMemorySaver

load_dotenv()

prompts = load_prompts()
conversation_prompt = prompts["conversationalist_prompt"]


CONVERSATIONAL_MODEL = "openai:gpt-5-nano"

_raw_agent = create_agent(
    model=CONVERSATIONAL_MODEL,
    system_prompt=conversation_prompt,
    checkpointer=InMemorySaver()
)


