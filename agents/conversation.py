from dotenv import load_dotenv
from langchain.agents import create_agent
from .load_prompts import load_prompts

load_dotenv()

prompts = load_prompts()
test_prompt = prompts["test_prompt"]


CONVERSATIONAL_MODEL = "openai:gpt-5-nano"

_raw_agent = create_agent(
    model=CONVERSATIONAL_MODEL,
    system_prompt=test_prompt
)


