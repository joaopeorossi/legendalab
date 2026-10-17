# CLAUDE.md — LegendaLab

Instruções para o Claude Code neste repositório. **Responda sempre em português.**

## Contexto

Projeto de portfólio de João Rossi (1º ano de ADS na FIAP).
Documentos de referência em `docs/privado/` (pasta local, fora do Git — nunca mover para fora dela nem citar o conteúdo em arquivos públicos):

- `OPERACAO_GLOBO_PROJECT_SOURCE_OF_TRUTH.md` — decisões (fonte de verdade).
- `LEGENDALAB_TECH_SPEC.md` — especificação técnica.
- `LEGENDALAB_ROADMAP.md` — etapas, prompts, critérios de aceite e testes de entendimento.
- `GUIA_PREPARACAO_E0.md` — preparação do ambiente.

Quando um prompt citar `docs/ARQUIVO.md`, leia em `docs/privado/ARQUIVO.md`.

O LegendaLab gera legendas em português para pessoas surdas, mede o erro da transcrição (WER), aponta blocos difíceis de ler (limites do *Guia para Produções Audiovisuais Acessíveis*, 2016) e marca trechos de baixa confiança.

## Modo de trabalho (obrigatório)

João não escreve o código, mas **precisa entender cada linha** e conseguir explicá-la numa entrevista.

1. **Plano antes do código:** explique o plano em até 8 linhas e liste os arquivos que vai criar ou alterar. Espere a aprovação.
2. **Blocos pequenos:** implemente em partes de até ~40 linhas. Depois de cada bloco, explique em português simples: o que faz, por que existe e qual alternativa foi descartada.
3. **Teste de entendimento no fim da etapa:** faça as perguntas da etapa no roadmap e proponha a mudança-teste. **Não dê as respostas antes de João tentar.** Peça que ele preveja o resultado antes de rodar.
4. **Uma etapa por vez:** trabalhe só na etapa atual do roadmap.

## Escopo

- Implemente apenas o que está na etapa atual e na spec. Não adicione funcionalidades, dependências ou arquivos fora disso sem perguntar.
- Se achar que uma decisão registrada deveria mudar, **proponha e espere**. Decisões novas viram registro em `docs/decisions/`.
- **Proibido:** conteúdo, marca ou visual da Globo; resumo ou reescrita de texto por LLM; APIs pagas de transcrição; executar comandos que gerem custo na nuvem sem avisar antes.

## Código

- Python 3.11+, com tipagem e funções pequenas.
- Nomes de código em inglês; comentários, mensagens de erro e textos de interface em português.
- Dependências com versão fixa em `requirements.txt`.
- Limites e cortes (legibilidade, confiança, duração, tamanho) sempre em configuração, nunca fixos no meio do código.

## Testes

- Toda regra de negócio tem teste em `pytest`, incluindo as fronteiras.
- Testes de pipeline e de API usam um **Transcriber falso**, determinístico.

## Segurança e dados

- Nunca `shell=True`. Chamar ffmpeg/ffprobe com lista de argumentos.
- Nunca usar o nome original do arquivo enviado; salvar com UUID em pasta temporária e apagar em `finally`.
- Nunca registrar em log o texto transcrito nem o nome original do arquivo.
- Segredos só em variáveis de ambiente; `.env` no `.gitignore`.
- **Nunca commitar áudio do Common Voice** (os termos proíbem re-hospedar). `data/` fica no `.gitignore`. Nunca tentar identificar quem fala.

## Honestidade

- Não afirmar resultados que não foram medidos. Números do README vêm de `results/`.
- Sugira mensagens de commit, mas João aprova ou reescreve.
