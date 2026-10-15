# Nightreign Overlay

Overlay de cronômetro das fases do dia para **Elden Ring Nightreign**, com visual em preto, cinza e azul escuro.
Ele **lê a tela** (como o OBS faz) e sincroniza sozinho com o jogo, em **português ou inglês**. Não injeta nada no jogo e não mexe nos arquivos dele.

## Instalação (1 passo)
1. Extraia a pasta e dê dois cliques em **`INSTALAR.bat`**.
2. Ele instala o que precisa (e o Python via winget, se faltar) e cria **`NightreignOverlay.exe` na mesma pasta**.
3. Abra o `NightreignOverlay.exe`. Na primeira vez o leitor de texto leva alguns segundos para carregar.

> O instalador usa Python 3.10 a 3.13 (instala o 3.12 sozinho se faltar). Python 3.14 não é compatível com o leitor de texto.

> Rode o jogo em **Janela sem bordas** (ou janela). O overlay não aparece sobre a tela cheia exclusiva.

## Como as fases mudam
As fases **só avançam quando o sinal aparece na tela**. Se o tempo zerar antes, o cronômetro passa a contar **negativo** (vermelho) até o sinal chegar.

| Sinal lido | O que acontece |
|---|---|
| Banner **DIA I / DIA II / DIA III** (centro) | Começa o dia (Dia III vira cronômetro progressivo) |
| *"A maré da Noite se fortalece."* / *"The Night's tide grows stronger."* (canto superior direito) | 1º círculo começa a fechar |
| *"A chuva se acumula, pressagiando a maré da Noite"* / *"Rains gather, portending the tide of Night"* | 2º círculo começa a fechar |

Tempos padrão (editáveis no `config.json`, em segundos): zona livre 270 · 1º círculo fecha em 180 · do 1º ao 2º sinal 360 · 2º círculo até o chefe 180.
Esses valores são suposições (4:30 / 3 min) baseadas no que a comunidade observou. Ajuste se medir outros tempos.

## Atalhos
| Tecla | Ação |
|---|---|
| F5 | Avançar o dia manualmente |
| F6 | Modo mover (arraste o overlay; aperte F6 de novo para salvar a posição) |
| F7 | Avançar a fase manualmente |
| F8 | Mostrar/ocultar |
| F9 | Zerar |
| F10 | Fechar |
| F11 | Modo depuração (mostra o texto que o OCR está lendo) |

## Teste com vídeo do YouTube
- Coloque o vídeo em **tela cheia** (tecla F) no monitor principal, em 1080p ou mais.
- O overlay não é capturado por ele mesmo, então não se confunde com os próprios textos.
- Se o vídeo estiver em janela, coloque em `config.json`: `"window_title": "YouTube"`.
- Aperte **F11** para ver o que ele está lendo. Se não detectar, veja `nightreign_overlay.log` (mesma pasta) e ajuste `regions` no `config.json` (frações da tela: esquerda, topo, direita, base).
- Se o jogo estiver em outro idioma, adicione as frases em `extra_phrases` no `config.json`.

## Arquivos
`NightreignOverlay.py` (app) · `nr_logic.py` (fases e reconhecimento) · `config.json` · `INSTALAR.bat` · `test_logic.py`
