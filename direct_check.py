from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env", override=True)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

r = client.embeddings.create(
    model="text-embedding-3-small",
    input="test embedding"
)

print(len(r.data[0].embedding))