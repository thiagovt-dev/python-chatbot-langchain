from langchain.memory import ConversationBufferMemory
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
import os
from dotenv import load_dotenv
from tkinter import Tk
from tkinter.filedialog import asksaveasfilename
from vosk import Model, KaldiRecognizer
import pyaudio
from gtts import gTTS
import pygame
import ctypes

# Função para desabilitar os logs do Vosk
def disable_vosk_logs():
    if os.name == "posix":
        libc = ctypes.CDLL(None)
        devnull = os.open(os.devnull, os.O_RDWR)
        libc.dup2(devnull, 2)

# Função para desabilitar os logs da ALSA
def disable_alsa_logs():
    if os.name == "posix":
        f = open(os.devnull, 'w')
        os.dup2(f.fileno(), 2)

# Desabilita os logs do Vosk e ALSA
disable_vosk_logs()
disable_alsa_logs()

# Carrega variáveis de ambiente
load_dotenv()

# Template do prompt para o modelo de linguagem
template = """
You are a virtual assistant. 
Respond in English or Portuguese depending on the input language.

Input: {input}
"""
base_prompt = PromptTemplate(input_variables=["input"], template=template)

# Inicializa o modelo de linguagem e memória de conversação
llm = ChatGroq(model_name="llama3-8b-8192")
memory = ConversationBufferMemory(memory_key="chatbot_history", input_key='input')
llm_chain = LLMChain(llm=llm, prompt=base_prompt, memory=memory)

# Limpa o terminal
os.system("clear")

conversation_history = []

# Inicializa o modelo de reconhecimento de voz do Vosk (português)
model = Model("dictionary/pt-br/vosk-model-pt-fb-v0.1.1-20220516_2113")  # Caminho para o modelo de português
recognizer = KaldiRecognizer(model, 16000)

# Inicializa o PyAudio para capturar áudio do microfone
mic = pyaudio.PyAudio()
stream = mic.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=8192)
stream.start_stream()

# Função para sintetizar voz usando gTTS e reproduzir com pygame
def speak(text, lang='en'):
    if lang == 'pt':
        lang = 'pt-br'
    
    tts = gTTS(text, lang=lang)
    tts.save("response.mp3")
    
    pygame.mixer.init()
    pygame.mixer.music.load("response.mp3")
    pygame.mixer.music.play()
    
    while pygame.mixer.music.get_busy():
        pass
    
    os.remove("response.mp3")

# Função para capturar input de voz usando Vosk (captura contínua)
def listen():
    print("Listening...")
    while True:
        data = stream.read(4096)
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            text = result.split('"text" : ')[-1].strip('"}\n')
            if text == "<UNK>" or len(text.strip()) == 0:
                print("Nenhuma fala válida detectada, tentando novamente...")
                continue
            print(f"You said: {text}")
            return text

# Função para detectar o idioma do texto
def detect_language(text):
    if any(char in text for char in "ãõáéíóúçâêô"):
        return 'pt'
    else:
        return 'en'

# Loop principal da aplicação
while True:
    user_input = listen()

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
        speak("Tchau!", lang='pt')
        break
    
    # Invoca o modelo de linguagem para gerar a resposta
    response = llm_chain.invoke({'input': user_input})
    bot_response = response['text']

    # Detecta o idioma do input e ajusta a resposta
    language = detect_language(user_input)
    
    # Armazena o histórico da conversa
    conversation_history.append(f"You: {user_input}")
    conversation_history.append(f"Bot: {bot_response}")
    
    # Exibe e fala a resposta do bot
    print(f"Bot: {bot_response}")
    speak(bot_response, lang=language)
