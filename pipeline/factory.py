import aiohttp

from services import stt_deepgram, tts_minimax, transport_vad

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.frameworks.langchain import LangchainProcessor

from .converters import TranscriptionToContextConverter

# Your LangChain agent
from agents import conversation_agent

# Session logging
from logs import setup_session_logger

async def pipeline():
    async with aiohttp.ClientSession() as session:

        # Local mic/speaker
        transport = transport_vad()

        # Speech-to-Text
        stt = stt_deepgram()

        # LLM (LangChain agent instead of OpenAI directly)
        llm = LangchainProcessor(chain=conversation_agent)

        # Text-to-Speech (MiniMax with custom params)
        tts = tts_minimax(session)

        # Simple frame converter (agent handles memory via InMemorySaver)
        converter = TranscriptionToContextConverter()

        # Session logger - extracts config dynamically from services
        session_logger = setup_session_logger(stt, tts, conversation_agent.model)

        pipeline = Pipeline([
            transport.input(),
            stt,
            converter,
            llm,
            tts,
            transport.output(),
        ])

        task = PipelineTask(pipeline)
        runner = PipelineRunner()

        try:
            await runner.run(task)
        finally:
            session_logger.close()
