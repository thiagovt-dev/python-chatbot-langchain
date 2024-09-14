from pydub import AudioSegment
from pydub.playback import play
from langchain.memory import ConversationBufferMemory
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
import os
import logging
from dotenv import load_dotenv
from tkinter import Tk
from tkinter.filedialog import asksaveasfilename
from vosk import Model, KaldiRecognizer
import pyaudio
from gtts import gTTS
import ctypes
from langdetect import detect, LangDetectException 

def disable_vosk_logs():
    if os.name == "posix":
        libc = ctypes.CDLL(None)
        devnull = os.open(os.devnull, os.O_RDWR)
        libc.dup2(devnull, 2)

def disable_alsa_logs():
    if os.name == "posix":
        f = open(os.devnull, 'w')
        os.dup2(f.fileno(), 2)

disable_vosk_logs()
disable_alsa_logs()

load_dotenv()

template = """
You are a virtual assistant. 
Respond in English or in Brazilian Portuguese depending on the input language.

Input: {input}
"""
base_prompt = PromptTemplate(input_variables=["input"], template=template)

llm = ChatGroq(model_name="llama3-8b-8192")
memory = ConversationBufferMemory(memory_key="chatbot_history", input_key='input')
llm_chain = LLMChain(llm=llm, prompt=base_prompt, memory=memory)

os.system("clear")

conversation_history = []

mic = pyaudio.PyAudio()
stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
stream.start_stream()

def speak(text, lang='en', speed=1.2):
    if lang == 'pt':
        lang = 'pt-br'
    
    tts = gTTS(text, lang=lang)
    tts.save("response.mp3")
    
    audio = AudioSegment.from_mp3("response.mp3")
    fast_audio = audio.speedup(playback_speed=speed)

    play(fast_audio)
    
    os.remove("response.mp3")

def listen(model_pt, model_en):
    print("Pressione 'Enter' para iniciar a gravação...")
    input() 
    print("Fale agora. Quando terminar, pressione 'Enter' novamente.")
    
    recognizer_pt = KaldiRecognizer(model_pt, 16000)
    recognizer_en = KaldiRecognizer(model_en, 16000)
    
    while True:
        data = stream.read(4096)
        if recognizer_pt.AcceptWaveform(data):
            result = recognizer_pt.Result()
            text = result.split('"text" : ')[-1].strip('"}\n')
            if text != "<UNK>":
                print(f"You said (PT): {text}")
                input("Pressione 'Enter' para confirmar...") 
                return text, 'pt'
        
        # Se falhar, tenta com o modelo de inglês
        elif recognizer_en.AcceptWaveform(data):
            result = recognizer_en.Result()
            text = result.split('"text" : ')[-1].strip('"}\n')
            if text != "<UNK>":
                print(f"You said (EN): {text}")
                input("Press 'Enter' to confirm...") 
                return text, 'en'

def detect_language(text):
    try:
        language = detect(text)
        if language == 'pt':
            return 'pt'
        elif language == 'en':
            return 'en'
        else:
            return 'en'  
    except LangDetectException:
        return 'en'

model_pt = Model("dictionary/pt-br/vosk-model-small-pt-0.3")
model_en = Model("dictionary/en/vosk-model-small-en-us-0.15")

while True:
    print("Aguardando sua fala...")

    user_input, detected_language = listen(model_pt, model_en)

    if user_input is None:
        continue

    if user_input.lower() == "sair":
        save_conversation = input("Deseja salvar a conversa? (sim/não): ").strip().lower()
        if save_conversation == "sim":
            root = Tk()
            root.withdraw()
            file_path = asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
            if file_path:
                with open(file_path, "w") as file:
                    file.write("\n".join(conversation_history))
                print(f"Conversa salva em '{file_path}'.")
            root.destroy()
        print("Bot: Tchau!")
        speak("Tchau!", lang='pt', speed=1.2) 
        break
    
    print("Gerando resposta, por favor aguarde...")

    response = llm_chain.invoke({'input': user_input})
    bot_response = response['text']

    conversation_history.append(f"You: {user_input}")
    conversation_history.append(f"Bot: {bot_response}")
    
    speak(bot_response, lang=detected_language, speed=1.2)
    print(f"Bot: {bot_response}")
