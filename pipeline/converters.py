"""
Simple frame converters for Pipecat pipelines.
"""

from pipecat.frames.frames import Frame, TranscriptionFrame, LLMContextFrame
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.processors.aggregators.llm_context import LLMContext


class TranscriptionToContextConverter(FrameProcessor):
    """Converts TranscriptionFrame to LLMContextFrame.

    Unlike LLMContextAggregatorPair, does NOT track history.
    Use when your LLM agent handles memory itself (e.g., InMemorySaver).
    """

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            # Create minimal context with just the user message
            context = LLMContext([{"role": "user", "content": frame.text}])
            await self.push_frame(LLMContextFrame(context=context))
        else:
            await self.push_frame(frame, direction)
