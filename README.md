# LegendaLab

Legendas automáticas em português para pessoas surdas, com medição do erro da transcrição e aviso dos trechos em que a IA está insegura.

> 🚧 Em construção (outubro de 2026). Acompanhe o progresso em [LEARNING_LOG.md](LEARNING_LOG.md).

## Resultados: qual modelo usar?

Comparei dois tamanhos do Whisper, rodando no próprio computador (sem API paga), nas **427 frases do conjunto de teste do Common Voice pt-BR**, com 2 núcleos de CPU, imitando a máquina da demo.

| Modelo | Erro de palavra (WER) | Velocidade (RTF) |
|---|---|---|
| whisper-base | 38,6% | 0,32 |
| whisper-small | 22,9% | 0,86 |

- **WER:** palavras trocadas, faltando ou sobrando, divididas pelas palavras da frase correta, somando todas as frases.
- **RTF:** tempo de processamento ÷ duração do áudio. RTF 0,32 = 10 s de áudio transcritos em 3,2 s.
- **Regra de escolha:** o menor WER entre os modelos com RTF até 0,5. **Modelo da demo: whisper-base.**

**Conclusão:** o small erra bem menos (22,9% contra 38,6%), mas com 2 núcleos leva 0,86 s para cada segundo de áudio, acima do limite que defini para a demo responder rápido. Por isso a demo usa o base, e é justamente por ele errar mais que a marcação dos trechos duvidosos é importante.

**Onde o modelo erra:** as frases com mais erros são listas de termos técnicos e nomes próprios, e em duas o modelo entrou em repetição ("e o hábita e o hábita e o hábita"). As 10 piores estão em [errors.md](results/2026-10-24_145853/errors.md).

Medido em 24/10/2026 · seed 42 · normalização v1 · dados completos em [results/2026-10-24_145853](results/2026-10-24_145853/).
