print("\033[92m[SUCCES]\033[0m Main launched")
print("If that long for launch is normal, we need to load some huge library and that can take long time to load.")

# ======================================================
#
# Imports
#
# ======================================================

from threading import Thread
import customtkinter as ctk
import sounddevice as sd
from model import Model
import soundfile as sf
import numpy as np
import asyncio
import dotenv
import json
import copy
import os

# ======================================================
#
# Data
#
# ======================================================

data = {
    "device-map": "cpu",
    "llm-config": {
        "api-url": "",
        "model-id": ""
    },
    "stt-config": {
        "model-id": "turbo",
        "compute-type": "int8",
        "beam-size": 5
    },
    "tts-config": {
        "model-id": "k2-fsa/OmniVoice",
        "num-step": 16
    },
    "models": []
}

def save():
    with open("data.json", "w+", encoding="UTF-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load():
    global data
    with open("data.json", "r", encoding="UTF-8") as f:
        data = json.load(f)

# ======================================================
#
# Main Functions
#
# ======================================================

def switch_record():
    if not window.is_recording:
        if window.model:
            window.controls[1].configure(text="\U0001F399 Stop recording", fg_color="#e31e2b", hover_color="#c51f2a")
            
            window.stream = sd.InputStream(callback=save_audio_part, samplerate=window.fs, channels=1)
            window.stream.start()
            
            print("\033[92m[START]\033[0m Recording")
        else:
            widget = ctk.CTkToplevel()
            label = ctk.CTkLabel(widget, text="Start a model before launch record.")
            label.pack(padx=80, pady=40)
            return
    else:
        window.controls[1].configure(text="\U0001F399 Start recording", fg_color="#1871E6", hover_color="#175FBE")
        
        window.stream.stop()
        window.stream.close()
        
        # On compile et on sauvegarde
        if window.audio_buffer:
            full_audio = np.concatenate(window.audio_buffer, axis=0)
            sf.write("input.wav", full_audio, window.fs)
            print("\033[92m[SUCCESS]\033[0m Recording saved to input.wav")
            
            # On lance le traitement après l'arrêt manuel
            Thread(target=start_process).start()
        print("\033[92m[SUCCES]\033[0m Recording")
    
    window.is_recording = not window.is_recording

def save_audio_part(indata, *args, **kwargs):
    if window.is_recording:
        window.audio_buffer.append(indata.copy())

def start_process():
    print("\033[92m[START]\033[0m Generate response")
    try:
        asyncio.run(window.model.generate(
            "input.wav",
            data["llm-config"]["model-id"],
            window.model_info["ref-audio"],
            window.model_info["ref-text"],
            None,
            data["stt-config"]["beam-size"]
        ))
        
        audio, fs = sf.read("output.wav")
        sd.play(audio, fs)
        
        print("\033[92m[SUCCES]\033[0m Generate response")
    except Exception as e:
        print()
        print(f"\033[91m[ERROR]\033[0m {e}")
        

# ======================================================
#
# Models Functions
#
# ======================================================

def update(*args):
    global data
    new_data = copy.deepcopy(data)
    for i, model in enumerate(window.models):
        new_data["models"][i]["prompt"] = model.prompt_textbox.get("0.0", "end-1c")
        new_data["models"][i]["ref-audio"] = model.ref_audio_entry.get()
        new_data["models"][i]["ref-text"] = model.ref_text_textbox.get("0.0", "end-1c")
    
    new_data["llm-config"]["api-url"] = window.llm_config.api_url_entry.get()
    new_data["llm-config"]["model-id"] = window.llm_config.model_id_entry.get()
    dotenv.set_key(".env", "API-KEY", window.llm_config.api_key_entry.get(), quote_mode="never")
    
    new_data["stt-config"]["model-id"] = window.stt_config.model_id_entry.get()
    new_data["stt-config"]["compute-type"] = window.stt_config.compute_type_entry.get()
    new_data["stt-config"]["beam-size"] = int(window.stt_config.beam_size_entry.get())
    
    new_data["tts-config"]["model-id"] = window.tts_config.model_id_entry.get()
    new_data["tts-config"]["num-step"] = int(window.tts_config.num_step_entry.get())
    
    if new_data != data:
        data = new_data
        save()

def select_model(model_id: str):
    widget = ctk.CTkToplevel()
    label = ctk.CTkLabel(widget, text="Wait for another pop up before select another model or recording!")
    label.pack(padx=80, pady=40)
    
    def _select_model():
        try:
            if window.model:
                window.model.shutdown()
                del window.model
            
            for model in data["models"]:
                if model["model-id"] == model_id:
                    window.model_info = model
                    break
            
            window.model = Model(
                data["tts-config"]["model-id"],
                data["llm-config"]["api-url"],
                data["device-map"],
                data["tts-config"]["num-step"],
                window.model_info["prompt"],
                data["stt-config"]["model-id"],
                data["stt-config"]["compute-type"]
            )
            widget = ctk.CTkToplevel()
            label = ctk.CTkLabel(widget, text="Model loaded.")
            label.pack(padx=80, pady=40)
        except Exception as e:
            print(f"\033[91m[ERROR]\033[0m {e}")
    t = Thread(target=_select_model)
    t.start()
        

def new_model():
    widget = ctk.CTkInputDialog(title="Create new model", text="Name of the model: ")
    name = widget.get_input()
    if name:
        data["models"].append({
            "model-id": name,
            "prompt": "",
            "ref-audio": "",
            "ref-text": ""
        })
        
        window.models.append(Accordeon(is_model=True, model_data=data["models"][-1]))
        save()
        window.add_new.forget()
        window.add_new.pack(pady=(0, 10))

def delete_model(model_id: str):
    global models, data
    
    widget = ctk.CTkInputDialog(title="Delete model", text=f"Type '{model_id}' if you are sure to do that")
    sure = widget.get_input()
    if sure != model_id:
        widget = ctk.CTkToplevel()
        label = ctk.CTkLabel(widget, text="Delete model cancelled.")
        label.pack(padx=80, pady=40)
        return
    
    for i, model in enumerate(data["models"]):
        if model["model-id"] == model_id:
            models[i].destroy()
            models.pop(i)
            data["models"].pop(i)
    save()

def number_entry(c):
    if c.isdigit():
        return True
    else:
        return False

# ======================================================
#
# Class
#
# ======================================================

class Accordeon(ctk.CTkFrame):
    def __init__(self, text: str|None = None, elements: tuple|list = [], is_model: bool = False, model_data: dict|None = None):
        super().__init__(window.config_frame, corner_radius=0)
        self.is_open = False
        if is_model:
            self.base_text = "Model " + model_data["model-id"]
            self.model_data = model_data
        else:
            self.base_text = text
        
        self.btn = ctk.CTkButton(self, 360, corner_radius=0, text="▶ "+self.base_text, command=self.switch, anchor="w")
        self.frame = ctk.CTkFrame(self, width=330, corner_radius=0)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)
        
        if is_model:
            self.prompt_label = ctk.CTkLabel(self.frame, text="Prompt :", anchor="nw")
            self.ref_audio_label = ctk.CTkLabel(self.frame, text="Ref audio path :")
            self.ref_text_label = ctk.CTkLabel(self.frame, text="Ref text :")
            
            self.prompt_label.grid(row=0, column=0)
            self.ref_audio_label.grid(row=1, column=0)
            self.ref_text_label.grid(row=2, column=0)
            
            self.prompt_textbox = ctk.CTkTextbox(self.frame, height=100, wrap="word")
            self.ref_audio_entry = ctk.CTkEntry(self.frame, 200)
            self.ref_text_textbox = ctk.CTkTextbox(self.frame, height=100, wrap="word")
            
            self.prompt_textbox.insert("0.0", model_data["prompt"])
            self.ref_audio_entry.insert("0", model_data["ref-audio"])
            self.ref_text_textbox.insert("0.0", model_data["ref-text"])
            
            self.prompt_textbox.grid(row=0, column=1, pady=(0, 10))
            self.ref_audio_entry.grid(row=1, column=1, pady=(0, 10))
            self.ref_text_textbox.grid(row=2, column=1)
            
            self.select = ctk.CTkButton(self.frame, text="Select model", fg_color="#27bb27", hover_color="#229c22", command=lambda: select_model(model_data["model-id"]))
            self.delete = ctk.CTkButton(self.frame, text="Delete model", fg_color="#e31e2b", hover_color="#c51f2a", command=lambda: delete_model(model_data["model-id"]))
            
            self.select.grid(row=4, columnspan=2, pady=(20, 0))
            self.delete.grid(row=5, columnspan=2, pady=(20, 0))
        else:
            self.model_id_label = ctk.CTkLabel(self.frame, text="model id :")
            self.model_id_entry = ctk.CTkEntry(self.frame, 200)
            
            if text == "LLM configuration":
                self.api_url_label = ctk.CTkLabel(self.frame, text="api url :")
                self.api_key_label = ctk.CTkLabel(self.frame, text="api key :")
                
                self.api_url_label.grid(row=0, column=0)
                self.model_id_label.grid(row=1, column=0)
                self.api_key_label.grid(row=2, column=0)
                
                self.api_url_entry = ctk.CTkEntry(self.frame, 200)
                self.api_key_entry = ctk.CTkEntry(self.frame, 200, show="*")
                
                self.api_url_entry.insert("0", data["llm-config"]["api-url"])
                self.model_id_entry.insert("0", data["llm-config"]["model-id"])
                self.api_key_entry.insert("0", os.getenv("API-KEY") or "")
        
                self.api_url_entry.grid(row=0, column=1)
                self.model_id_entry.grid(row=1, column=1)
                self.api_key_entry.grid(row=2, column=1)
            elif text == "Whisper STT configuration":
                self.compute_type_label = ctk.CTkLabel(self.frame, text="Compute type :")
                self.beam_size_label = ctk.CTkLabel(self.frame, text="Beam size :")
                
                self.model_id_label.grid(row=0, column=0)
                self.compute_type_label.grid(row=1, column=0)
                self.beam_size_label.grid(row=2, column=0)
                
                self.compute_type_entry = ctk.CTkEntry(self.frame, 200)
                self.beam_size_entry = ctk.CTkEntry(self.frame, 200, validate="key", validatecommand=vcmd)
                
                self.model_id_entry.insert("0", data["stt-config"]["model-id"])
                self.compute_type_entry.insert("0", data["stt-config"]["compute-type"])
                self.beam_size_entry.insert("0", data["stt-config"]["beam-size"])
                
                self.model_id_entry.grid(row=0, column=1)
                self.compute_type_entry.grid(row=1, column=1)
                self.beam_size_entry.grid(row=2, column=1)
            elif text == "OmniVoice TTS configuration":
                self.num_step_label = ctk.CTkLabel(self.frame, text="Num step :")
                self.model_id_label.grid(row=0, column=0)
                self.num_step_label.grid(row=1, column=0)
                
                self.num_step_entry = ctk.CTkEntry(self.frame, 200, validate="key", validatecommand=vcmd)
                self.model_id_entry.grid(row=0, column=1)
                self.num_step_entry.grid(row=1, column=1)
                
                self.model_id_entry.insert("0", data["tts-config"]["model-id"])
                self.num_step_entry.insert("0", data["tts-config"]["num-step"])
                
        self.btn.pack()
        self.pack(pady=(0, 10))
    
    def switch(self):
        if self.is_open:
            self.btn.configure(text="▶ "+self.base_text)
            self.frame.forget()
        else:
            self.btn.configure(text="▼ "+self.base_text)
            self.frame.pack(padx=15)
        
        self.is_open = not self.is_open

# ======================================================
#
# Init
#
# ======================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.is_recording = False
        self.audio_buffer = []
        self.fs = 44100
        self.model: Model|None = None
        self.model_info: dict|None = None
    
    def init(self):
        self.title("AI TTS Respond")
        self.geometry("720x480")
        self.resizable(False, False)
        self.grid_columnconfigure(0, minsize=360, weight=1)
        self.grid_columnconfigure(1, minsize=360, weight=1)

        control_frame = ctk.CTkFrame(self, 360, 480, 0, fg_color="#3B3B3B")
        control_frame.grid(row=0, column=0, sticky="nsew")

        self.controls = [
            ctk.CTkLabel(control_frame, text="AI TTS Respond", font=("aria", 25, "bold")),
            ctk.CTkButton(control_frame, corner_radius=10, text="\U0001F399 Start recording", font=("aria", 20), anchor="center", fg_color="#1871E6", hover_color="#175FBE", command=switch_record)
        ]

        for control in self.controls: control.pack(pady=10)

        self.config_frame = ctk.CTkScrollableFrame(self, 360, 480, 0)
        self.config_frame._scrollbar.configure(width=0)
        self.config_frame.grid(row=0, column=1, sticky="nsew")
        
        
        if "data.json" not in os.listdir():
            save()
        load()
        
        self.llm_config = Accordeon("LLM configuration")
        self.stt_config = Accordeon("Whisper STT configuration")
        self.tts_config = Accordeon("OmniVoice TTS configuration")
        self.models = [Accordeon(is_model=True, model_data=model_data) for model_data in data["models"]]
        self.add_new = ctk.CTkButton(self.config_frame, 360, text="Create new model", corner_radius=0, fg_color="#27bb27", hover_color="#229c22", command=new_model)
        self.add_new.pack(pady=(0, 10))
        
        print("\033[92m[START]\033[0m Open GUI")
        self.bind("<KeyRelease>", update)
        

if __name__ == "__main__":
    dotenv.load_dotenv()
    
    window = App()
    vcmd = (window.register(number_entry), '%P')
    window.init()
    window.mainloop()
    if window.model:
        window.model.shutdown()
    
    print("\033[92m[SUCCES]\033[0m Exit")