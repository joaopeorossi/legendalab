# Imagem da demo do LegendaLab para o Azure Container Apps (DR-13). Quem monta é o GitHub Actions
# (.github/workflows/docker-image.yml), a cada push na main.

# Python 3.12, o mesmo do desenvolvimento, em versão enxuta (Debian slim) para a imagem ficar menor
FROM python:3.12-slim

# Log sai na hora (sem buffer), sem arquivos .pyc, e o lugar onde ficam os pesos do modelo
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/app/.cache/huggingface

# ffmpeg e ffprobe, usados pelo core/media.py; apagar a lista de pacotes deixa a imagem menor
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Usuário sem privilégios: se alguém explorar uma falha do app, não vira administrador do container
RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Dependências antes do código: o Docker reaproveita esta camada enquanto o requirements.txt não muda
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Só o que a demo precisa (results/ alimenta o /api/benchmark); dados, testes e documentos ficam de fora
COPY core/ core/
COPY api/ api/
COPY web/ web/
COPY results/ results/

# Daqui em diante, tudo roda como o usuário sem privilégios
USER app

# Baixa os pesos do modelo padrão (escolhido pela RN6) durante o build: nada é baixado a cada inicialização
RUN python -c "from core import config; from faster_whisper import WhisperModel; WhisperModel(config.DEFAULT_MODEL, device=config.DEVICE, compute_type=config.COMPUTE_TYPE)"

# Depois do build, nunca buscar o modelo na internet. Na nuvem, o upload vai até 30 MB (decisão mantida no DR-12),
# abaixo dos 50 MB do padrão local: vídeo menor sobe mais rápido pelo celular.
ENV HF_HUB_OFFLINE=1 \
    PORT=8080 \
    MAX_UPLOAD_MB=30
EXPOSE 8080

# Servidor em todas as interfaces, na porta 8080 (a "Target port" configurada no Azure Container Apps);
# "exec" faz o uvicorn receber o sinal de desligar quando o Azure desliga a réplica
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
