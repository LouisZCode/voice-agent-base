"""
Simple frame converters for Pipecat pipelines.
"""

from pipecat.frames.frames import (
    Frame,
    TranscriptionFrame,
    LLMContextFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.processors.aggregators.llm_context import LLMContext


class TranscriptionToContextConverter(FrameProcessor):
    """Converts TranscriptionFrame to LLMContextFrame with VAD gating.

    Buffers transcriptions while user is speaking.
    Only sends to LLM after user stops speaking.
    Does NOT track history (agent uses InMemorySaver).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._buffer = ""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            # User started - clear buffer for new utterance
            self._buffer = ""
            await self.push_frame(frame, direction)

        elif isinstance(frame, TranscriptionFrame):
            # Accumulate transcription text
            self._buffer += frame.text + " "

        elif isinstance(frame, UserStoppedSpeakingFrame):
            # User stopped - send accumulated text to LLM
            if self._buffer.strip():
                context = LLMContext([{"role": "user", "content": self._buffer.strip()}])
                await self.push_frame(LLMContextFrame(context=context))
            self._buffer = ""
            await self.push_frame(frame, direction)

        else:
            # Pass all other frames through
            await self.push_frame(frame, direction)
