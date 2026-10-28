# Diário de aprendizado — LegendaLab

Registro público de como aprendi cada parte deste projeto. Uma entrada por etapa.

---

### 2026-10-17 — E0: preparação do ambiente
- **O que aprendi:** o PATH é a lista de pastas onde o terminal procura os programas. Quando digitei `python` e o Windows mandou abrir a Microsoft Store, era porque o Python não estava nessa lista.
- **O que me confundiu:** instalei o ffmpeg e o terminal continuou dizendo que ele não existia. Só funcionou depois de fechar e abrir o terminal de novo, porque ele só lê o PATH quando abre.
- **Uma decisão que tomei:** usar o recorte em português do Brasil do Common Voice (427 frases de teste), em vez do pacote completo de 4,8 GB. Tem a frase correta de cada áudio, que é o que eu preciso para medir, e é o mesmo português de quem vai usar a legenda.

---

### 2026-10-23 — B1: transcrever e medir o erro
O LegendaLab agora pega um áudio curto de alguém falando em português e transforma em texto, e sabe em que segundo cada palavra foi dita e o quanto a IA estava segura de cada uma. Depois ele compara esse texto com a frase que a pessoa realmente leu e conta quantas palavras saíram trocadas, faltando ou sobrando: esse é o erro da transcrição, chamado WER. Também mede a velocidade, quanto tempo o computador levou para transcrever, comparado com a duração do áudio.

- **O que aprendi:** antes de comparar, os dois textos precisam ser padronizados. No primeiro teste ("Quero um misto quente"), o modelo acertou todas as palavras, mas colocou um ponto no final. Sem tirar a pontuação, só esse ponto já daria 25% de erro. Também entendi por que o WER pode passar de 100%: palavras a mais não têm limite, então, se o modelo inventa texto, o erro passa do tamanho da frase.
- **O que me confundiu:** a transcrição quebrou logo no começo sem eu ter mexido em nada. O pip instalou a versão mais nova do PyAV (a biblioteca que abre o áudio), e ela tinha tirado uma coisa que o faster-whisper ainda usa. Entendi que "mais novo" não quer dizer "compatível", e por isso as versões ficam fixas no `requirements.txt`.
- **Uma decisão que tomei:** na hora de medir, manter os acentos e tirar a pontuação. Acento muda a palavra ("e" e "é", "esta" e "está"), então errar o acento tem que contar como erro. Pontuação não é palavra. O lado ruim é que o meu WER não mede pontuação, e isso fica como limitação.

---

### 2026-10-24 — B2: benchmark dos 2 modelos
Medi os dois tamanhos do Whisper nas 427 frases do conjunto de teste inteiro do Common Voice pt-BR. O small errou 22,9% das palavras e o base, 38,6%, mas o small levou 0,86 s para cada segundo de áudio. Pela regra que defini antes de ver os números (o menor erro entre os que levam até 0,5 s por segundo de áudio), a demo usa o base.

- **O que aprendi:** o modelo mais preciso nem sempre é o que dá para usar. Com 2 núcleos de CPU, o small fica perto do tempo real e o base é quase 3 vezes mais rápido. Também vi onde o modelo mais erra: listas de termos técnicos e nomes próprios ("lotusscript", "Piccadilly"), e em duas frases ele entrou em repetição ("e o hábita e o hábita e o hábita").
- **O que me confundiu:** durante os 45 minutos da rodada, o terminal não mostrava progresso nenhum. O Python guarda as mensagens num buffer quando a saída vai para um arquivo e só solta tudo no fim. Resolvi com `flush=True` no print do progresso.
- **Uma decisão que tomei:** medir com 2 threads, igual às 2 vCPUs que a demo vai ter na nuvem, e não com os 4 que o faster-whisper usa por padrão. Assim a regra de velocidade vale para a máquina da demo. Também tirei o custo estimado da tabela: era só uma conta com o preço público e não ajudava quem usa a legenda.

---

### 2026-10-24 — B3: legenda, legibilidade e baixa confiança
O LegendaLab agora divide a transcrição em blocos de legenda que respeitam o Guia de 2016 (até 2 linhas de 37 caracteres e até 6 segundos), gera o arquivo WebVTT que o player do navegador entende e aponta os blocos rápidos ou longos demais para ler. Também marca os trechos em que a IA estava insegura. Testei essa marcação nas 427 frases do benchmark: as frases marcadas tiveram 51,4% de erro, contra 16,8% nas demais.

- **O que aprendi:** o algoritmo guloso da quebra em blocos. Ele vai pondo palavras no bloco enquanto cabe e, quando não cabe, fecha o bloco e abre outro, sem voltar atrás. A velocidade de leitura (caracteres por segundo) não entra nessa decisão, porque dividir o bloco não deixa a fala mais lenta; ela só é apontada depois. O sistema aponta, mas não reescreve o texto.
- **O que me confundiu:** a marcação funcionou, mas marcou 60% das frases do modelo base. Fiquei entre marcar menos e deixar passar mais erros: com o corte em 0,3, só 30% das frases seriam marcadas, mas só 54% dos erros cairiam nelas.
- **Uma decisão que tomei:** manter o corte de 0,5 que defini antes de medir. Assim, 84% dos erros caem em frases marcadas, e quem não confere pelo áudio é avisado da maioria deles. Escolher o corte olhando o próprio conjunto de teste deixaria o número ajustado aos dados. O lado ruim são muitos destaques, e isso fica como limitação.

---

### 2026-10-24 — B4: API e página
Agora dá para enviar um vídeo por uma página e assistir com a legenda. O servidor confere o arquivo antes de gastar processamento (tamanho, tipo real, duração e se tem áudio), extrai o áudio, gera a legenda e apaga tudo no fim, inclusive quando dá erro. A página toca o próprio arquivo da pessoa com a legenda e lista os blocos, com ⚠ nos duvidosos e um rótulo nos difíceis de ler.

- **O que aprendi:** o tipo do arquivo vem do conteúdo, não da extensão. O ffprobe reconhece um áudio salvo como `.txt` e recusa um texto salvo como `.mp4`. E o ffmpeg e o ffprobe são chamados com uma lista de argumentos, sem shell, então um nome de arquivo como `; rm -rf ~` vira só um argumento, nunca um comando.
- **O que me confundiu:** o FastAPI lê o upload inteiro antes de chegar na minha função. Conferir o tamanho só durante a cópia não impediria alguém de mandar um arquivo gigante. Por isso o servidor também recusa pelo tamanho declarado no pedido, antes de ler o arquivo.
- **Uma decisão que tomei:** o modelo da demo fica no `config.py`, e um teste confere se ele é o mesmo que a regra de escolha aponta no último benchmark. Se alguém mudar o limite de velocidade e a regra passar a escolher outro modelo, o teste quebra e avisa.

---

### 2026-10-24 — B5: README final
Reescrevi o README para alguém de fora entender o projeto em 2 minutos: o problema, o que o LegendaLab faz, os resultados do benchmark, um diagrama do fluxo, como rodar, as limitações e as fontes. O GIF da demo entra depois.

- **O que aprendi:** todo número do README precisa vir de um arquivo em `results/`. Eu ia citar que as frases marcadas como duvidosas concentram 84% dos erros, mas essa conta tinha sido feita fora do benchmark. Acrescentei a conta ao `calibrate.py` e rodei de novo antes de citar.
- **O que me confundiu:** a regra `data/` do `.gitignore`, que protege os áudios do Common Voice, ignorava qualquer pasta chamada `data`, inclusive a `tests/data` com o arquivo esperado de um teste. O teste ficaria fora do GitHub sem eu perceber. Renomeei a pasta para `tests/fixtures`.
- **Uma decisão que tomei:** declarar como limitação que a legenda não descreve sons (música, risos) nem identifica quem fala. Uma legenda feita para surdos normalmente tem isso, e quem conhece o assunto vai notar a falta.

---

### 2026-10-26 — Revisão da regra do modelo (DR-12)
Mudei o modelo da demo do base para o small. A regra antiga pedia RTF até 0,5 e escolhia o base, que erra 38,6% das palavras. Agora a regra é "mais rápido que o tempo real" (RTF até 1,0), e a demo usa o small, que erra 22,9%.

- **O que aprendi:** para quem não ouve, o número que mais importa não é o WER, é o erro sem aviso: a palavra errada numa frase que não ganhou ⚠. Com o small, 8,6% das palavras saem erradas sem aviso; com o base, 6,2%. O small erra menos no total, mas marca menos frases (33% contra 60%), então deixa mais erros passarem sem destaque.
- **O que me confundiu:** se mudar a regra depois de ver os números era trapaça. Entendi a diferença: ajustar o corte de confiança olhando o teste mudaria o próprio número da calibração, mas a regra do modelo só escolhe qual versão vai para a demo e não muda nenhum número medido. Mesmo assim, deixei os resultados dos dois modelos no README e escrevi que a regra mudou.
- **Uma decisão que tomei:** aceitar mais erros sem aviso em troca de muito menos erros no total. Com o base, 6 em cada 10 frases tinham ⚠, e quando quase tudo tem aviso, o aviso perde o sentido.

---
