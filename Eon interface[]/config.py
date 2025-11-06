import os

# Busca as chaves das "Variáveis de Ambiente" do seu computador
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_ORGANIZATION = os.environ.get("OPENAI_ORGANIZATION")

# Verificação para garantir que o app não rode sem as chaves
if not OPENAI_API_KEY:
    raise ValueError("A variável de ambiente 'OPENAI_API_KEY' não foi definida.")

if not OPENAI_ORGANIZATION:
    raise ValueError("A variável de ambiente 'OPENAI_ORGANIZATION' não foi definida.")
