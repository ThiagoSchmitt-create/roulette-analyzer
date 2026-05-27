# Matemática Honesta sobre Roleta

Este documento existe para ser **lido antes** de qualquer aposta com dinheiro real, e para alinhar expectativas sobre o que este sistema pode e não pode fazer.

## A premissa do jogo

Em uma roleta **bem calibrada e bem operada**, cada giro é um experimento de Bernoulli independente sobre 37 (europeia) ou 38 (americana) bolsos equiprováveis.

| Roda | Bolsos | P(qualquer número) | House edge |
|---|---|---|---|
| Europeia | 37 (0–36) | 1/37 = 2,703% | **−2,70%** |
| Americana | 38 (0–36 + 00) | 1/38 = 2,632% | **−5,26%** |

O house edge vem do fato de que o payout (35:1 numa aposta straight) é menor que as odds verdadeiras (36:1 na europeia, 37:1 na americana).

## O teorema do "nenhuma estratégia funciona"

Para qualquer estratégia $S$ que aposta apenas em eventos da roleta:

$$\text{EV}(S) = \sum_i p_i \cdot \text{payout}_i = -\text{house edge}$$

Isso vale **independentemente** de:
- Quanto tempo você jogou
- Quais números saíram antes
- Se você dobra, multiplica, soma Fibonacci, espera padrões, etc.

**Por quê?** Linearidade da expectativa: a soma das EVs de cada aposta individual é o que conta. Como cada aposta tem EV negativo, a soma é negativa. Estratégias só **redistribuem a variância** — substituem muitas perdas pequenas por raras perdas grandes (Martingale) ou vice-versa (Paroli).

A simulação Monte Carlo no nosso `core/strategies.py` demonstra empiricamente:

```
estrategia         media   mediana    p(ruina)    p(lucro)
flat              968.64    960.00       0.000       0.337
martingale        888.28   1320.00       0.344       0.598
fibonacci         924.85   1150.00       0.185       0.737
dalembert         865.06   1090.00       0.247       0.543
paroli            951.89    950.00       0.000       0.375
```

Note que **todas as médias estão abaixo do bankroll inicial de 1000** — o house edge sempre vence no longo prazo.

## Falácias comuns

| Falácia | Verdade |
|---|---|
| "Esse número não sai há 50 giros, está atrasado" | Cada giro é independente; o passado não condiciona o futuro |
| "Vermelho saiu 8 vezes seguidas, preto deve sair" | Mesma falácia (Gambler's fallacy) |
| "Vou recuperar com Martingale" | Você terá lucros constantes pequenos até uma sequência ruim te zerar; EV inalterado |
| "Existem 'sistemas' vendidos que funcionam" | Se funcionassem, o vendedor estaria rico jogando, não vendendo o sistema |

## O ÚNICO edge historicamente comprovado

**Viés mecânico em rodas físicas**, detectado por análise estatística de milhares de giros. Casos famosos:

- **Joseph Jagger (1873)** — primeiro a explorar viés no Cassino de Monte Carlo. Ganhou ~£325k (~£30M hoje).
- **Edward Thorp + Claude Shannon (1961)** — construíram computador de bolso para wheel clocking; demonstraram edge mas problemas de hardware no cassino.
- **The Eudaemons (1977-1978)** — Doyne Farmer e Norman Packard usaram computador embutido em sapato para prever octante via física do giro.
- **Família García-Pelayo (1991-1994)** — Casino Gran Madrid: coletaram milhares de giros por roda, identificaram desvios consistentes, lucraram >$1M antes do cassino corrigir as rodas e tentar (sem sucesso) processá-los na justiça.

### Por que o método García-Pelayo funcionou (e ainda pode funcionar, em tese)

1. **Rodas mecânicas envelhecem.** Cone desbalanceado, bolsos com desgaste diferencial, eixo levemente inclinado — qualquer um produz viés estatístico.
2. **Com $\geq 3000$ giros** de uma roda específica, chi-square detecta desvios de ~2pp na probabilidade de bolsos individuais.
3. **Se um número aparece $\sim$ 3,7% das vezes** (ao invés dos 2,7% teóricos), a aposta straight nele tem $\text{EV} = 36 \times 0,037 - 1 = +0,332$ → **edge de 33%**.
4. **Kelly fraction** dá o tamanho ótimo da aposta para crescer bankroll.

### Por que provavelmente **não** funciona hoje

1. **Cassinos modernos monitoram suas próprias rodas** — softwares como TCS John Huxley fazem isso continuamente.
2. **Rodas são trocadas/recalibradas** a cada poucos meses.
3. **Você seria expulso** se identificado coletando milhares de giros sem apostar (ou apostando consistentemente nos mesmos números).
4. **Roletas online usam RNG auditado** — não há viés físico.

## O que este sistema **pode** legitimamente fazer

| Capacidade | Caso de uso |
|---|---|
| Auditar uma roda específica | Você quer testar se um cassino tem uma roda enviesada (estudo, jornalismo) |
| Auditar um RNG online | Você suspeita que um cassino online é dishonesto e quer evidência estatística |
| Mostrar empiricamente o house edge | Educação: mostrar a amigos por que Martingale não funciona |
| Calcular tamanho de amostra necessário | Planejar quantos giros precisam ser coletados para conclusão |
| Calibrar EV de apostas com smoothing | Sob suspeita de viés, calcular EV honesto antes de apostar |

## O que este sistema **não pode** fazer

| ❌ Não pode |
|---|
| Prever o próximo número numa roda justa |
| Garantir lucro em qualquer estratégia |
| Detectar viés com 100 giros (variância domina) |
| Substituir a observação cuidadosa de uma roda física específica |
| Funcionar sob coleta de baixa qualidade (OCR ruim, dados embaralhados) |

## Recomendação ética

Se você está construindo este sistema:
- **Para estudar matemática e estatística aplicada:** ótimo, é um caso clássico riquíssimo.
- **Para auditar um cassino suspeito:** legítimo, especialmente com dados públicos (alguns cassinos publicam históricos).
- **Para ganhar dinheiro consistentemente:** matemática diz que não vai dar certo. Considere usar o mesmo conjunto de skills em algo onde há sinal real (mercado financeiro, otimização operacional, etc.).

Se você está jogando com dinheiro real, defina um **bankroll que pode perder sem consequências** e trate como entretenimento. Use Kelly fraction se quiser dimensionar entretenimento de forma matematicamente sã.
