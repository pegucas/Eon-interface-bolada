from flask import Flask, request, jsonify, send_file, render_template, url_for
from flask_cors import CORS
from openai import OpenAI
import os
import uuid
import base64
from urllib.parse import unquote
import json
from config import OPENAI_API_KEY, OPENAI_ORGANIZATION

# arquivo de chaves da API arquivo config.py
client = OpenAI(
    api_key=OPENAI_API_KEY,
    organization=OPENAI_ORGANIZATION
)

app = Flask(__name__)
CORS(app)

# --- Rotas das Páginas HTML ---

@app.route("/")
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route("/pergunta_nome")
def pergunta_nome():
    """Página para perguntar o nome"""
    return render_template('pergunta_nome.html')

@app.route("/mundo_perfeito")
def mundo_perfeito():
    """Página para descrever o mundo perfeito"""
    nome = request.args.get('nome', 'Usuário')
    return render_template('mundo_perfeito.html', nome=nome)

@app.route("/resultado")
def resultado():
    """Página para mostrar o resultado"""
    # Lógica de ODS removida daqui. Página simplificada.
    nome = request.args.get('nome', 'Usuário')
    mundo_perfeito = request.args.get('mundo_perfeito', 'Descrição não disponível')
    imagem_url = request.args.get('imagem_url', '')
    
    return render_template('resultado.html', 
                           nome=nome, 
                           mundo_perfeito=mundo_perfeito, 
                           imagem_url=imagem_url)

# --- Rotas da API e Arquivos ---

@app.route("/imagem/<filename>")
def servir_imagem(filename):
    """Servir imagem local"""
    try:
        return send_file(f'imagens/{filename}')
    except Exception as e:
        return f"Erro ao carregar imagem: {str(e)}", 404

@app.route("/audio/<filename>")
def servir_audio(filename):
    """Servir áudio local"""
    try:
        return send_file(f'audios/{filename}')
    except Exception as e:
        return f"Erro ao carregar áudio: {str(e)}", 404

# ÁUDIO FIXO - QUAL o seu nome ?
@app.route("/audio_pergunta")
def audio_pergunta():
    """Servir áudio fixo da pergunta do nome"""
    try:
        return send_file('audios/audio_pergunta_nome.mp3')
    except Exception as e:
        return f"Erro ao carregar áudio: {str(e)}", 404

# ÁUDIO PERSONALIZADO
@app.route("/audio_personalizado/<nome>")
def audio_personalizado(nome):
    """Servir áudio personalizado com nome - gera automaticamente se não existir"""
    try:
        # Decodificar o nome da URL
        nome_decodificado = unquote(nome)
        
        # Criar pasta audios se não existir
        if not os.path.exists('audios'):
            os.makedirs('audios')
        
        # Criar nome do arquivo sanitizado
        nome_arquivo_sanitizado = nome_decodificado.lower().replace(' ', '_').replace('/', '_').replace('\\', '_')
        nome_arquivo = f"audios/audio_{nome_arquivo_sanitizado}.mp3"
        
        # Se o arquivo não existe, gerar automaticamente
        if not os.path.exists(nome_arquivo):
            texto = f"Olá, {nome_decodificado}, como você imagina o mundo perfeito?"
            
            resposta = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=texto
            )
            
            with open(nome_arquivo, 'wb') as f:
                f.write(resposta.read())
        
        return send_file(nome_arquivo)
    except Exception as e:
        return f"Erro ao carregar áudio: {str(e)}", 404

# Gerar imagem (Rota principal com validação)
@app.route("/gerar", methods=["POST"])
def gerar():
    data = request.json
    nome = data.get("nome")
    mundo_perfeito = data.get("mundo_perfeito")

    if not nome:
        return jsonify({"erro": "Informe o nome"}), 400

    if not mundo_perfeito:
        return jsonify({"erro": "Informe como você imagina o mundo perfeito"}), 400

    try:
        # --- ETAPA 1: VALIDAÇÃO ODS 13 ---
        # Este prompt agora é rigoroso e focado apenas na ODS 13.
        analise_ods_prompt = f"""
        Analise o seguinte prompt de usuário e verifique se ele está ESPECIFICAMENTE focado na ODS 13: Ação Climática.
        Prompt: "{mundo_perfeito}"

        A ODS 13 foca em: combate às mudanças climáticas, energias renováveis, redução de emissões, resiliência climática, desastres naturais, políticas climáticas.
        Prompts gerais sobre "natureza", "árvores" ou "animais felizes" NÃO são ODS 13, a menos que estejam no contexto de MUDANÇA CLIMÁTICA (ex: "reflorestamento para captura de carbono", "cidade verde para reduzir calor").

        Responda APENAS com um objeto JSON válido com uma chave:
        1. "alinhado_ods13": um booleano (true se estiver claramente focado na ODS 13, false caso contrário).
        """
        
        resposta_analise = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "Você é um especialista rigoroso na ODS 13 (Ação Climática) da ONU e responde apenas em JSON."},
                {"role": "user", "content": analise_ods_prompt}
            ]
        )
        
        try:
            analise_data = json.loads(resposta_analise.choices[0].message.content)
        except json.JSONDecodeError:
            analise_data = {"alinhado_ods13": False}

        # --- O PORTÃO DE VALIDAÇÃO ---
        # Se não estiver alinhado, bloqueia a geração e retorna um erro 400.
        if not analise_data.get("alinhado_ods13", False):
            return jsonify({
                "erro": "Visão inválida. O seu prompt deve ser focado especificamente na ODS 13: Ação Climática (combate às mudanças climáticas, energias renováveis, redução de emissões, etc.)."
            }), 400


        # --- ETAPA 2: Enriquecer Prompt para Imagem (Só executa se passar da Etapa 1) ---
        resposta = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "Você é um especialista em prompts para geração de imagens. Crie prompts concisos e diretos (máximo 20 palavras) para imagens realistas. Responda APENAS com o prompt melhorado, sem explicações."},
                {"role": "user",
                 "content": f"Enriqueça este prompt de forma concisa para imagem realista: 'mundo perfeito com {mundo_perfeito}'. Adicione apenas detalhes essenciais de iluminação e realismo. Máximo 20 palavras. e não gere coisas que não poderam existir, que fuja da realidade, quando isso acontecer retire da imagem."}
            ]
        )
        prompt_enriquecido = resposta.choices[0].message.content

        # Criar pasta imagens se não existir
        if not os.path.exists('imagens'):
            os.makedirs('imagens')

        # --- ETAPA 3: Gerar Imagem ---
        imagem = client.images.generate(
            model="dall-e-3",
            prompt=f"Photorealistic: {prompt_enriquecido}. High quality, realistic lighting, detailed.",
            size="1792x1024",
            response_format="b64_json"
        )

        b64_imagem = imagem.data[0].b64_json
        img_bytes = base64.b64decode(b64_imagem)

        filename = f"{uuid.uuid4()}.png"
        filepath = os.path.join("imagens", filename)

        with open(filepath, "wb") as f:
            f.write(img_bytes)

        # Usar url_for para gerar a URL
        local_url = url_for('servir_imagem', filename=filename, _external=True)

        # --- ETAPA 4: Retornar sucesso ---
        # Não precisa mais enviar dados da ODS
        return jsonify({
            "nome": nome,
            "mundo_perfeito": mundo_perfeito,
            "imagem_url": local_url
        })

    except Exception as e:
        return jsonify({"erro": f"Erro ao gerar conteúdo: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5501)