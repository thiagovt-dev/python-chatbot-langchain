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
import pyaudio
from gtts import gTTS
import ctypes
import speech_recognition as sr
import traceback

# Desativando logs do Vosk e ALSA
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
    try:
        if lang == 'pt':
            lang = 'pt-br'
        
        tts = gTTS(text, lang=lang)
        tts.save("response.mp3")
        
        mp3_audio = AudioSegment.from_mp3("response.mp3")
        fast_audio = mp3_audio.speedup(playback_speed=speed)

        play(fast_audio)

        os.remove("response.mp3")
    except Exception as e:
        print(f"Erro ao gerar ou reproduzir o áudio: {e}")
        traceback.print_exc()

def listen():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Ajustando para ruído de fundo...")
        r.adjust_for_ambient_noise(source)
        print("Fale agora:")
        audio = r.listen(source)

    try:
        print("Reconhecendo em português...")
        text_pt = r.recognize_google(audio, language='pt-BR')
        print(f"Você disse (PT): {text_pt}")
        return text_pt, 'pt'
    except sr.UnknownValueError:
        print("Não entendi em português, tentando com o inglês.")
        try:
            text_en = r.recognize_google(audio, language='en-US')
            print(f"You said (EN): {text_en}")
            return text_en, 'en'
        except sr.UnknownValueError:
            print("Não consegui reconhecer o áudio em nenhum idioma.")
            return None, None
    except sr.RequestError as e:
        print(f"Erro no serviço de reconhecimento de fala: {e}")
        return None, None

while True:
    print("Aguardando sua fala...")

    user_input, detected_language = listen()

    if user_input is None:
        continue

    # Aguarda a tecla "Enter" antes de gerar a resposta
    input("Pressione 'Enter' para gerar a resposta...")

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

    try:
        response = llm_chain.invoke({'input': user_input})
        bot_response = response['text']

        conversation_history.append(f"You: {user_input}")
        conversation_history.append(f"Bot: {bot_response}")
        
        speak(bot_response, lang=detected_language, speed=1.2)
        print(f"Bot: {bot_response}")
    except Exception as e:
        print(f"Ocorreu um erro ao gerar a resposta: {e}")
        traceback.print_exc()
