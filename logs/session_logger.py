"""
Session Logger for Pipecat Pipeline

Intercepts pipecat debug logs to extract timing and transcription.
Writes clean, human-readable session logs.
"""

import os
import re
from datetime import datetime
from pathlib import Path


class SessionLogger:
    """
    Logs voice conversation sessions by intercepting pipecat debug messages.

    Tracks:
    - Session start/end with duration
    - User transcriptions with STT timing
    - LLM responses with generation timing
    - TTS with synthesis timing
    """

    def __init__(self, log_dir: str = "logs/conversations"):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        self._session_start = datetime.now()

        # Daily log file (append mode)
        today = self._session_start.strftime("%Y-%m-%d")
        self._log_file = self._log_dir / f"{today}.log"
        self._file = open(self._log_file, "a", encoding="utf-8")

        # Timing trackers
        self._user_started_ts = None
        self._llm_started_ts = None
        self._tts_started_ts = None

    def write_header(self, config: dict = None):
        """Write session header with config. Call AFTER services are created."""
        self._file.write("=" * 70 + "\n")
        self._file.write(f"SESSION START: {self._session_start.strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._file.write("=" * 70 + "\n\n")

        if config:
            for service, params in config.items():
                if isinstance(params, dict):
                    params_str = ", ".join(f"{k}={v}" for k, v in params.items())
                else:
                    params_str = str(params)
                self._file.write(f"[CONFIG] {service}: {params_str}\n")
            self._file.write("\n")

        self._file.write("--- CONVERSATION ---\n\n")
        self._file.flush()

    def _write(self, message: str):
        """Write a line to log file."""
        self._file.write(message + "\n")
        self._file.flush()

    def _time_str(self) -> str:
        """Current time formatted."""
        return datetime.now().strftime("%H:%M:%S")

    def _calc_duration_secs(self, start_ts: datetime) -> float:
        """Calculate seconds since start timestamp."""
        if not start_ts:
            return 0.0
        delta = datetime.now() - start_ts
        return round(delta.total_seconds(), 1)

    # --- Event handlers called from loguru sink ---

    def on_user_started_speaking(self):
        """Called when VAD detects user started speaking."""
        self._user_started_ts = datetime.now()

    def on_user_stopped_speaking(self):
        """Called when VAD detects user stopped speaking."""
        pass  # We log when we get the transcription

    def on_transcription(self, text: str):
        """Called when STT produces transcription."""
        duration = self._calc_duration_secs(self._user_started_ts)
        self._write(f"[{self._time_str()}] USER (STT: {duration}s): \"{text}\"")
        self._user_started_ts = None
        self._llm_started_ts = datetime.now()  # LLM starts now

    def on_llm_response(self, text: str):
        """Called when LLM response is sent to TTS."""
        duration = self._calc_duration_secs(self._llm_started_ts)
        # Truncate if too long
        display = text[:150] + "..." if len(text) > 150 else text
        self._write(f"[{self._time_str()}] LLM ({duration}s): \"{display}\"")
        self._llm_started_ts = None
        self._tts_started_ts = datetime.now()  # TTS starts now

    def on_bot_stopped_speaking(self):
        """Called when TTS audio playback finished."""
        duration = self._calc_duration_secs(self._tts_started_ts)
        if duration > 0:  # Only log if we tracked TTS start
            self._write(f"[{self._time_str()}] TTS ({duration}s): Audio finished\n")
        self._tts_started_ts = None

    def close(self):
        """Close session and write footer."""
        session_end = datetime.now()
        duration = session_end - self._session_start

        self._file.write("\n" + "=" * 70 + "\n")
        self._file.write(f"SESSION END: {session_end.strftime('%Y-%m-%d %H:%M:%S')} | Duration: {int(duration.total_seconds())}s\n")
        self._file.write("=" * 70 + "\n")
        self._file.close()

        print(f"Session log saved to: {self._log_file}")


def setup_session_logger(stt, tts, llm_model: str, log_dir: str = "logs/conversations"):
    """
    Create and configure session logger from service objects.
    Extracts config dynamically from STT and TTS services.

    Args:
        stt: DeepgramSTTService instance
        tts: MiniMaxHttpTTSService instance
        llm_model: LLM model name string
        log_dir: Directory for log files

    Returns:
        SessionLogger instance (already configured with loguru sink)
    """
    from loguru import logger

    session_logger = SessionLogger(log_dir=log_dir)
    session_logger.write_header({
        "deepgram": {
            "language": stt._settings.get("language"),
            "model": stt._settings.get("model"),
        },
        "minimax": {
            "model": tts._model_name,
            "voice_id": tts._voice_id,
            "language": tts._settings.get("language_boost"),
            "speed": tts._settings.get("voice_setting", {}).get("speed"),
        },
        "llm": {"model": llm_model},
    })
    logger.add(create_pipecat_log_sink(session_logger), filter="pipecat")

    return session_logger


def create_pipecat_log_sink(session_logger: SessionLogger):
    """
    Creates a loguru sink that intercepts pipecat logs and routes to SessionLogger.

    Usage:
        logger.add(create_pipecat_log_sink(session_logger), filter="pipecat")
    """
    def sink(message):
        text = message.record["message"]

        # User started speaking
        if "User started speaking" in text:
            session_logger.on_user_started_speaking()

        # User stopped speaking (transcription follows)
        elif "User stopped speaking" in text:
            session_logger.on_user_stopped_speaking()

        # Transcription received - extract user text
        elif "Invoking chain with" in text:
            match = re.search(r"Invoking chain with (.+)$", text)
            if match:
                session_logger.on_transcription(match.group(1))

        # LLM response sent to TTS - extract response text
        elif "Generating TTS" in text:
            match = re.search(r"Generating TTS \[(.+)\]$", text)
            if match:
                session_logger.on_llm_response(match.group(1))

        # Bot finished speaking
        elif "Bot stopped speaking" in text:
            session_logger.on_bot_stopped_speaking()

    return sink
