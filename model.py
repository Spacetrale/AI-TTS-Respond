from omnivoice import OmniVoice, OmniVoiceGenerationConfig
from concurrent.futures import ThreadPoolExecutor
from faster_whisper import WhisperModel
from openai import AsyncOpenAI
import asyncio
import torch
import os

class Model:
    def __init__(
        self,
        tts_model_id: str,
        llm_base_url: str,
        device_map: str = "cpu",
        num_step: int = 32,
        prompt: str = "",
        transcription_model: str = "turbo",
        compute_type: str = "float16"
        ):
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        self.tts_model = OmniVoice.from_pretrained(
            tts_model_id,
            device_map=device_map,
            dtype=torch.float16
        )
        self.config = OmniVoiceGenerationConfig(num_step)
        
        self.llm_model = AsyncOpenAI(
            api_key=os.getenv("API-KEY"),
            base_url=llm_base_url
        )
        self.history = [{"role": "system", "content": prompt}]
        
        self.whisper_model = WhisperModel(
            transcription_model,
            device=device_map.split(":")[0],
            compute_type=compute_type
        )
    
    async def _transcript_audio(
        self,
        audio_path: str,
        beam_size: int=5,
        ):
        loop = asyncio.get_event_loop()
        
        def _transcript():
            segments, info = self.whisper_model.transcribe(audio_path, beam_size=beam_size)
            return "".join([segment.text for segment in segments])
        
        return await loop.run_in_executor(self.executor, _transcript)
    
    async def _generate_text(self, text: str, llm_model_id: str):
        self.history.append({"role": "user", "content": text})
        
        completion = await self.llm_model.chat.completions.create(
            model=llm_model_id,
            messages=self.history
        )
        
        message = completion.choices[0].message.content
        self.history.append({"role": "assistant", "content": message})
        return message
    
    async def _generate_audio(
        self,
        text: str,
        ref_audio_path: str,
        ref_text: str|None = None,
        language: str|None = None
    ):
        loop = asyncio.get_event_loop()
        
        def _gen_audio(ref_text):
            if not ref_text:
                ref_text = self.tts_model.create_voice_clone_prompt(ref_audio_path).ref_text
                print(f"[REF-TEXT]: {ref_text}")
            
            audio = self.tts_model.generate(
                text,
                language,
                ref_text,
                ref_audio_path,
                generation_config=self.config
            )
            return audio[0]
        
        return await loop.run_in_executor(self.executor, _gen_audio, ref_text)
    
    async def generate(
        self,
        input_audio_path: str,
        llm_model_id: str,
        ref_audio_path: str,
        ref_text: str|None = None,
        language: str|None=None,
        beam_size:int=5,
        output_path: str="output.wav"
        ):
        text = await self._transcript_audio(input_audio_path, beam_size)
        output_text = await self._generate_text(text, llm_model_id)
        audio = await self._generate_audio(output_text, ref_audio_path, ref_text, language)
        
        if output_path:
            try:
                import soundfile as sf
                sf.write(output_path, audio, self.tts_model.sampling_rate)
                return output_path
            except ImportError:
                print("You don't have install soundfile")
        
        return audio
    
    def shutdown(self, wait: bool=True):
        self.executor.shutdown(wait)