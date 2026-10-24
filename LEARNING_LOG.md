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
