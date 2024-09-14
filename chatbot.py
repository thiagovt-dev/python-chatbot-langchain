from langchain.memory import ConversationBufferMemory
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate
import os
from dotenv import load_dotenv
from tkinter import Tk
from tkinter.filedialog import asksaveasfilename
from pocketsphinx import LiveSpeech
from gtts import gTTS
import pygame

# Carrega variáveis de ambiente
load_dotenv()

# Template do prompt para o modelo de linguagem
template = """
You are a virtual assistant. 
Respond in English.

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

# Função para sintetizar voz usando gTTS e reproduzir com pygame
def speak(text):
    tts = gTTS(text, lang='en')
    tts.save("response.mp3")
    
    # Inicializa o pygame mixer para tocar o áudio
    pygame.mixer.init()
    pygame.mixer.music.load("response.mp3")
    pygame.mixer.music.play()
    
    # Espera até a reprodução do áudio terminar
    while pygame.mixer.music.get_busy():
        pass
    
    # Remove o arquivo de áudio temporário
    os.remove("response.mp3")

# Função para capturar input de voz usando PocketSphinx (captura contínua)
def listen():
    print("Listening...")
    speech = LiveSpeech(dic='dictionary/en/cmusphinx-en-us-5.2/cmudict-en-us.dict',
                        hmm='dictionary/en/cmusphinx-en-us-5.2')
    for phrase in speech:
        print(f"You said: {phrase}")
        return str(phrase)

# Loop principal da aplicação
while True:
    user_input = listen()  # Substitui o input por reconhecimento de voz

    if user_input is None:
        continue  # Ignorar se nenhum input for recebido

    if user_input.lower() == "exit":
        save_conversation = input("Do you want to save the conversation? (yes/no): ").strip().lower()
        if save_conversation == "yes":
            root = Tk()
            root.withdraw()
            file_path = asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
            if file_path:
                with open(file_path, "w") as file:
                    file.write("\n".join(conversation_history))
                print(f"Conversation saved in '{file_path}'.")
            root.destroy()
        print("Bot: Goodbye!")
        speak("Goodbye!")  # Fala a despedida
        break
    
    # Invoca o modelo de linguagem para gerar a resposta
    response = llm_chain.invoke({'input': user_input})
    bot_response = response['text']

    # Armazena o histórico da conversa
    conversation_history.append(f"You: {user_input}")
    conversation_history.append(f"Bot: {bot_response}")
    
    # Exibe e fala a resposta do bot
    print(f"Bot: {bot_response}")
    speak(bot_response)  # Fala a resposta
