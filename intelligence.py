#!/usr/bin/env python3
import os
import pickle
import numpy as np
from openai import OpenAI
from sentence_transformers import SentenceTransformer

MOONSHOT_KEY = os.getenv('MOONSHOT_API_KEY')
MOONSHOT_ENDPOINT = os.getenv('MOONSHOT_API_ENDPOINT', 'https://api.moonshot.ai/v1')

_local_model = None
def get_local_model():
    global _local_model
    if _local_model is None:
        _local_model = SentenceTransformer('all-MiniLM-L6-v2')
    return _local_model

def get_moonshot_client():
    if not MOONSHOT_KEY:
        return None
    return OpenAI(api_key=MOONSHOT_KEY, base_url=MOONSHOT_ENDPOINT)

def generate_embedding(text):
    text = text[:2000]
    try:
        client = get_moonshot_client()
        if client:
            response = client.embeddings.create(model='moonshot-v1-8k', input=text)
            return np.array(response.data[0].embedding, dtype=np.float32)
    except Exception as e:
        print(f'Moonshot embedding failed: {e}')
    
    model = get_local_model()
    return model.encode(text, convert_to_numpy=True).astype(np.float32)

def generate_summary(article_title, article_summary, top_interests):
    prompt = f'''Article: {article_title}
Context: This user cares about {top_interests}.
Explain in 2 sentences why this matters to them.'''
    
    try:
        client = get_moonshot_client()
        if client:
            response = client.chat.completions.create(
                model='moonshot-v1-8k',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
    except Exception as e:
        print(f'Summary generation failed: {e}')
    
    return article_summary[:200] if article_summary else 'No summary available'

def compute_similarity(embedding1, embedding2):
    if embedding1 is None or embedding2 is None:
        return 0.0
    e1 = pickle.loads(embedding1) if isinstance(embedding1, bytes) else embedding1
    e2 = pickle.loads(embedding2) if isinstance(embedding2, bytes) else embedding2
    return float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2)))

def serialize_embedding(embedding):
    return pickle.dumps(embedding)