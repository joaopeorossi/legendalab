"""Configuração central: todos os números e opções ajustáveis do projeto ficam aqui."""

# Transcrição
LANGUAGE = "pt"  # idioma fixo: evita que o modelo "adivinhe" outro idioma
DEVICE = "cpu"  # o projeto roda sem placa de vídeo (no computador e na nuvem)
COMPUTE_TYPE = "int8"  # números de 8 bits: mais rápido e menos memória na CPU
CPU_THREADS = 2  # imita as 2 vCPU da demo no Cloud Run, para o RTF medido valer para a RN6
MODEL_SIZES = ("base", "small")  # tamanhos do Whisper comparados no benchmark

# Medição do erro (RN8: o WER sempre registra qual normalização usou)
NORMALIZATION_VERSION = "v1"

# Benchmark
SEED = 42  # RN10: mesma seed, mesmas frases sorteadas
RTF_LIMIT = 0.5  # RN6: o modelo da demo precisa ter RTF menor ou igual a este limite
ERRORS_REPORT_SIZE = 10  # quantas frases aparecem no errors.md
