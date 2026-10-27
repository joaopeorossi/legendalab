"""Configuração central: todos os números e opções ajustáveis do projeto ficam aqui."""

import os
from pathlib import Path

# Transcrição
LANGUAGE = "pt"  # idioma fixo: evita que o modelo "adivinhe" outro idioma
DEVICE = "cpu"  # o projeto roda sem placa de vídeo (no computador e na nuvem)
COMPUTE_TYPE = "int8"  # números de 8 bits: mais rápido e menos memória na CPU
CPU_THREADS = 2  # imita as 2 vCPU da demo no Azure Container Apps, para o RTF medido valer para a RN6
MODEL_SIZES = ("base", "small")  # tamanhos do Whisper comparados no benchmark

# Medição do erro (RN8: o WER sempre registra qual normalização usou)
NORMALIZATION_VERSION = "v1"

# Benchmark
SEED = 42  # RN10: mesma seed, mesmas frases sorteadas
RTF_LIMIT = 1.0  # RN6 (DR-12): o modelo da demo precisa ser mais rápido que o tempo real (era 0,5)
ERRORS_REPORT_SIZE = 10  # quantas frases aparecem no errors.md

# Legibilidade (RN7: Guia para Produções Audiovisuais Acessíveis, MinC/SAv, 2016)
MAX_LINES = 2  # linhas por bloco de legenda
MAX_CHARS_PER_LINE = 37  # caracteres por linha
CPS_WARNING = 15  # acima disto (caracteres por segundo): aviso
CPS_VIOLATION = 18  # acima disto: violação
MIN_CUE_S = 1.0  # duração mínima de um bloco, em segundos
MAX_CUE_S = 6.0  # duração máxima de um bloco, em segundos

# Baixa confiança: valores iniciais (os três primeiros são os padrões do próprio Whisper),
# ajustados olhando os erros reais na calibração (bench/calibrate.py)
LOW_CONF_MAX_NO_SPEECH_PROB = 0.6  # acima disto: provável trecho sem fala
LOW_CONF_MIN_AVG_LOGPROB = -1.0  # abaixo disto: modelo inseguro no trecho
LOW_CONF_MAX_COMPRESSION_RATIO = 2.4  # acima disto: texto repetitivo demais
LOW_CONF_MIN_WORD_PROBABILITY = 0.5  # abaixo disto: alguma palavra duvidosa
REPETITION_MAX_NGRAM = 4  # procura trechos repetidos de 1 até este número de palavras
REPETITION_MIN_REPEATS = 3  # quantas vezes seguidas o trecho precisa aparecer

# Demo (API): os dois limites vêm de variável de ambiente, com estes valores como padrão,
# para poderem mudar sem mexer no código
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "50"))  # RN2: tamanho máximo do upload
MAX_DURATION_S = float(os.environ.get("MAX_DURATION_S", "60"))  # RN1: duração máxima do vídeo
UPLOAD_FORM_MARGIN_BYTES = 1024 * 1024  # folga para os cabeçalhos do formulário no Content-Length
DEFAULT_MODEL = "small"  # RN6 (DR-12): escolhido pelo benchmark do B2 (conferido em tests/test_api.py)
FFPROBE_TIMEOUT_S = 15  # tempo máximo para o ffprobe analisar o arquivo
FFMPEG_TIMEOUT_S = 60  # tempo máximo para o ffmpeg extrair o áudio
# Formatos aceitos, pelo nome que o ffprobe dá ao conteúdo (não pela extensão do arquivo, RN3)
ALLOWED_FORMATS = {
    "mov", "mp4", "m4a", "3gp", "3g2", "mj2", "matroska", "webm", "avi",
    "mp3", "wav", "ogg", "flac", "aac", "mpegts", "asf",
}
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
