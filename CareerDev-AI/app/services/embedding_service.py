from typing import List
from openai import OpenAI

# ---------------------------------------------------------
# OPENAI CLIENT CONFIGURATION
# ---------------------------------------------------------
# O cliente procurará automaticamente por "OPENAI_API_KEY" nas variáveis de ambiente.
client = OpenAI()


def embed_text(text: str) -> List[float]:
    """
    Gera um vetor de embedding para o texto fornecido usando
    o modelo 'text-embedding-3-small' da OpenAI.
    """
    # 1. Validação simples para evitar chamadas de API desnecessárias
    if not text or not text.strip():
        return []

    # 2. Sanitização (Recomendação OpenAI: substituir newlines por espaços)
    clean_text = text.replace("\n", " ")

    try:
        # 3. Chamada à API
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=clean_text
        )
        
        # 4. Retorno do vetor
        return response.data[0].embedding

    except Exception as e:
        # Log de erro (em produção, use um logger adequado como logging ou sentry)
        print(f"Error generating embedding: {e}")
        # Retorna lista vazia em caso de falha para não quebrar o fluxo
        return []
