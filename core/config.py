"""Configuração central: todos os números e opções ajustáveis do projeto ficam aqui."""

# Transcrição
LANGUAGE = "pt"  # idioma fixo: evita que o modelo "adivinhe" outro idioma
DEVICE = "cpu"  # o projeto roda sem placa de vídeo (no computador e na nuvem)
COMPUTE_TYPE = "int8"  # números de 8 bits: mais rápido e menos memória na CPU
MODEL_SIZES = ("base", "small")  # tamanhos do Whisper comparados no benchmark

# Medição do erro (RN8: o WER sempre registra qual normalização usou)
NORMALIZATION_VERSION = "v1"
