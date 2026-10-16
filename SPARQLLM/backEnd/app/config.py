from dotenv import load_dotenv
import os

load_dotenv()

GRAPHDB_ENDPOINT = os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200/repositories/KG-SFT")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("MODEL", "openrouter/free")

# Configura i path di importazione
APP_DIR = os.path.dirname(os.path.abspath(__file__))  # backEnd/app
WORKSPACE_DIR = os.path.dirname(os.path.dirname(APP_DIR))  # c:/Users/manuv/Desktop/SPARQLLM/SPARQLLM
PARENT_DIR = os.path.dirname(WORKSPACE_DIR)  # c:/Users/manuv/Desktop/SPARQLLM

EXAMPLES_PATH = os.path.join(PARENT_DIR, "kgsft_examples.ttl")
VOID_PATH = os.path.join(PARENT_DIR, "kgsft_void.ttl")