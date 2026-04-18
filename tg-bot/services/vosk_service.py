import os
import wave
import json
from vosk import Model, KaldiRecognizer

class VoskService:
    def __init__(self):
        model_path = "/app/voice/vosk-model-small-ru-0.22"
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Модель Vosk не найдена: {model_path}")
        self.model = Model(model_path)

    def recognize(self, audio_path: str) -> str:
        wf = wave.open(audio_path, "rb")
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            raise ValueError("Аудио должно быть mono PCM 16kHz 16bit")

        rec = KaldiRecognizer(self.model, wf.getframerate())
        result_text = ""

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                result_text += result.get("text", "") + " "

        result = json.loads(rec.FinalResult())
        result_text += result.get("text", "")

        wf.close()
        return result_text.strip()

vosk_service = VoskService()
