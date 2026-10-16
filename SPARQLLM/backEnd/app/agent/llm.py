import sys
import os

# Configura i path di importazione
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL

#Configura e restituisce l'istanza LangChain ChatOpenAI puntata a OpenRouter
def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model=MODEL,
        temperature=temperature,
    )
