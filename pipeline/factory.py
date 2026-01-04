import aiohttp

from services import stt_deepgram, tts_minimax, transport_vad

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import LLMContextAggregatorPair
from pipecat.processors.frameworks.langchain import LangchainProcessor

# Your LangChain agent
from agents import test_agent

# Session logging
from logs import setup_session_logger

async def pipeline():
    async with aiohttp.ClientSession() as session:

        # Local mic/speaker
        transport = transport_vad()

        # Speech-to-Text
        stt = stt_deepgram()

        # LLM (LangChain agent instead of OpenAI directly)
        llm = LangchainProcessor(chain=test_agent)

        # Text-to-Speech (MiniMax with custom params)
        tts = tts_minimax(session)

        # Context + aggregators
        messages = [
            {"role": "system", "content": "Eres un asistente amigable. Responde de forma breve y conversacional en espanol."}
        ]
        context = LLMContext(messages)
        context_aggregator = LLMContextAggregatorPair(context)

        # Session logger - extracts config dynamically from services
        session_logger = setup_session_logger(stt, tts, test_agent.model)

        pipeline = Pipeline([
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ])

        task = PipelineTask(pipeline)
        runner = PipelineRunner()

        try:
            await runner.run(task)
        finally:
            session_logger.close()
