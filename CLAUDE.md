# CLAUDE.md — LegendaLab

Instruções para o Claude Code neste repositório. **Responda sempre em português.**

## Contexto

Projeto de portfólio de João Rossi (1º ano de ADS na FIAP).
Documentos de referência em `docs/privado/` (pasta local, fora do Git — nunca mover para fora dela nem citar o conteúdo em arquivos públicos):

- `PROJECT_SOURCE_OF_TRUTH.md` — decisões (fonte de verdade).
- `LEGENDALAB_TECH_SPEC.md` — especificação técnica.
- `LEGENDALAB_ROADMAP.md` — **v2**: blocos B1 a B7, prompts, arquivos e funções de cada bloco, critérios de aceite e testes de entendimento.
- `GUIA_PREPARACAO_E0.md` — preparação do ambiente.

Quando um prompt citar `docs/ARQUIVO.md`, leia em `docs/privado/ARQUIVO.md`.

O LegendaLab gera legendas em português para pessoas surdas, mede o erro da transcrição (WER), aponta blocos difíceis de ler (limites do *Guia para Produções Audiovisuais Acessíveis*, 2016) e marca trechos de baixa confiança.

## Modo de trabalho (obrigatório)

João não escreve o código, mas **precisa entender cada parte** e conseguir explicá-la numa entrevista.

1. **Plano antes do código:** em até 10 linhas, com os arquivos, classes e funções. **Use exatamente os nomes da seção "O que vai ser criado" do bloco no roadmap.** Espere a aprovação.
2. **Um bloco inteiro por vez:** implemente o bloco todo. Toda função e classe tem uma docstring de 1 linha em português dizendo o que faz e por quê.
3. **Ao terminar o bloco:** rode o `pytest`; explique cada arquivo em 2–3 frases e cada função em 1 frase, em português simples; aponte as 3 linhas mais importantes do bloco e diga qual alternativa foi descartada.
4. **Teste de entendimento:** faça as perguntas do bloco e proponha a mudança-teste. **Não dê as respostas antes de João tentar.** Peça que ele preveja o resultado antes de rodar. Depois, desfaça a mudança-teste.
5. **Só o bloco atual:** não adiante partes de blocos seguintes.

## Escopo

- Implemente apenas o que está no bloco atual do roadmap e na spec. Não adicione funcionalidades, dependências ou arquivos fora disso sem perguntar.
- Se achar que uma decisão registrada deveria mudar, **proponha e espere**. João registra as decisões na SoT.
- **Proibido:** conteúdo, marca ou visual de empresas reais; resumo ou reescrita de texto por LLM; APIs pagas de transcrição; executar comandos de nuvem (`gcloud` e similares) ou que gerem custo.

## Código

- Python 3.12, com tipagem e funções pequenas. Caminhos com `pathlib`.
- Rodar sempre com o Python do `.venv` (`.venv\Scripts\python` no Windows).
- **Abrir arquivos sempre com `encoding="utf-8"`** (o Windows usa outra codificação por padrão).
- Nomes de código em inglês; comentários, docstrings, mensagens de erro e textos de interface em português.
- Dependências com versão fixa em `requirements.txt`.
- Limites e cortes (legibilidade, confiança, duração, tamanho) sempre em `core/config.py`, nunca fixos no meio do código.

## Testes

- Toda regra de negócio tem teste em `pytest`, incluindo as fronteiras.
- Testes de pipeline e de API usam o `FakeTranscriber`, determinístico.

## Segurança e dados

- Nunca `shell=True`. Chamar ffmpeg/ffprobe com lista de argumentos e timeout.
- Nunca usar o nome original do arquivo enviado; salvar com UUID em pasta temporária e apagar em `finally`.
- Nunca registrar em log o texto transcrito nem o nome original do arquivo.
- Segredos só em variáveis de ambiente; `.env` no `.gitignore`.
- **Nunca commitar áudio ou vídeo.** `data/` fica no `.gitignore` (os termos do Common Voice proíbem re-hospedar). `results/` só tem CSV, JSON e Markdown.
- Do dataset, usar só as colunas `path` e `sentence`. Nunca usar `client_id`, `age`, `gender` ou `accents`, nunca tentar identificar quem fala e nunca publicar resultado por pessoa.

## Honestidade

- Não afirmar resultados que não foram medidos. Números do README vêm de `results/`.
- Sugira mensagens de commit, mas João aprova ou reescreve.
