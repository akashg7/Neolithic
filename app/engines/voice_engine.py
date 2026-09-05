"""
Voice Engine — Tier 3 (stretch).
TTS/STT via Bhashini API for vernacular language support.
Stub implementation — will be filled by Nikhil if time allows.
"""


class VoiceEngine:
    def __init__(self):
        self.api_key = None

    async def text_to_speech(self, text: str, language: str = "hi") -> str:
        """Convert text to speech audio. Returns audio URL."""
        # TODO: Integrate Bhashini/Sarvam TTS API
        raise NotImplementedError("Voice engine not yet implemented (Tier 3)")

    async def speech_to_text(self, audio_ref: str, language: str = "hi") -> dict:
        """Transcribe audio to text. Returns transcript + detected intent."""
        # TODO: Integrate Bhashini/Sarvam STT API
        raise NotImplementedError("Voice engine not yet implemented (Tier 3)")


voice_engine = VoiceEngine()
