<div align="center">
  <h1>Nightreign Overlay</h1>
  <p><strong>Um cronômetro de fases para Elden Ring Nightreign.</strong></p>
  <p>Monitore os dias e o fechamento dos círculos com um overlay discreto, inspirado na estética do jogo.</p>
</div>

---

## ✨ Sobre o projeto

O **Nightreign Overlay** acompanha as fases de uma expedição em *Elden Ring Nightreign*. Ele captura a imagem da tela e usa reconhecimento óptico de caracteres (OCR) para identificar os banners dos dias e as mensagens que anunciam o fechamento dos círculos.

O reconhecimento funciona com textos em **português e inglês**. O programa apenas lê o que está visível na tela: não injeta código no jogo nem modifica os arquivos dele.

## 🎮 Funcionalidades

- Detecção dos banners **DIA I, DIA II e DIA III** — também aceita `DAY I`, `DAY II` e `DAY III`.
- Reconhecimento automático das mensagens de fechamento dos círculos.
- Cronômetro regressivo das fases e progressivo durante o Dia III.
- Contagem negativa, em vermelho, quando o tempo estimado termina antes de o próximo sinal aparecer.
- Overlay sempre visível, com controles para mover, ocultar e ajustar a aparência.
- Atalhos de teclado e modo de depuração para conferir o texto reconhecido pelo OCR.
- Configuração de tempos, regiões de leitura e frases adicionais em `config.json`.

## 📦 Instalação

**Requisitos:** Windows e conexão com a internet durante a instalação. O instalador procura Python **3.10 a 3.13** e tenta instalar o Python 3.12 caso não encontre uma versão compatível.

1. Baixe o projeto e extraia os arquivos em uma pasta.
2. Execute `INSTALAR.bat`.
3. Aguarde a instalação das dependências e a criação de `NightreignOverlay.exe` na mesma pasta.
4. Abra o executável. Na primeira inicialização, o leitor de texto pode levar alguns segundos para carregar.

> **Importante:** configure *Elden Ring Nightreign* em **Janela sem bordas** ou **modo janela**. O overlay não aparece sobre o jogo em tela cheia exclusiva.

## ⌨️ Atalhos

| Tecla | Ação |
|---|---|
| `F5` | Avançar manualmente para o próximo dia |
| `F6` | Ativar/desativar o modo de mover; arraste o overlay e pressione novamente para salvar a posição |
| `F7` | Avançar manualmente a fase |
| `F8` | Mostrar ou ocultar o overlay |
| `F9` | Reiniciar o cronômetro |
| `F10` | Fechar o aplicativo |
| `F11` | Ativar/desativar a depuração do OCR |

Os atalhos podem ser alterados na seção `hotkeys` do arquivo `config.json`.

## ⏱️ Fases e tempos padrão

As fases mudam quando o programa reconhece o sinal correspondente na tela — **o cronômetro chegar a zero não avança a fase sozinho**.

| Configuração | Tempo padrão | Descrição |
|---|---:|---|
| `explore` | 270 s (4 min 30 s) | Zona livre no início do dia |
| `circle1_close` | 180 s (3 min) | Estimativa para o primeiro círculo fechar |
| `a_to_b` | 360 s (6 min) | Intervalo entre os sinais do primeiro e do segundo círculo |
| `b_to_boss` | 180 s (3 min) | Intervalo entre o sinal do segundo círculo e o chefe |

Esses tempos são estimativas iniciais e podem ser ajustados no `config.json` conforme suas medições.

## ⚙️ Configuração

O `config.json` fica na mesma pasta do aplicativo. Entre as opções disponíveis estão:

| Opção | Para que serve |
|---|---|
| `monitor` | Escolhe o monitor usado na captura quando uma janela compatível não é encontrada (`1` é o monitor principal). |
| `window_title` | Define a janela a capturar. Use `"auto"` para procurar o jogo, um texto para procurar pelo título da janela ou `""` para capturar o monitor. |
| `scan_interval` | Intervalo aproximado entre as leituras, em segundos. |
| `overlay` | Define posição (`x`, `y`), opacidade e escala. |
| `durations` | Ajusta os tempos das fases, em segundos. |
| `regions.banner` | Região da tela em que o programa procura o banner do dia. |
| `regions.message` | Região da tela em que procura as mensagens dos círculos. |
| `extra_phrases` | Permite adicionar frases para os sinais dos círculos em outros idiomas. |
| `hotkeys` | Personaliza as teclas de atalho. |

As regiões usam frações no formato `[esquerda, topo, direita, base]`, com valores entre `0` e `1`. Se o texto não for detectado, pressione `F11`, confira a leitura do OCR e ajuste as regiões conforme a posição dos avisos na tela.

## 🛠️ Executar pelo código-fonte

Com Python 3.10 a 3.13 instalado, abra o terminal na pasta do projeto e execute:

```bash
python -m pip install -r requirements.txt
python NightreignOverlay.py
```

Para executar os testes da lógica:

```bash
python test_logic.py
```

Se os testes passarem, o terminal exibirá `TODOS OS TESTES PASSARAM`.

## 🧩 Arquivos do projeto

| Arquivo | Descrição |
|---|---|
| `NightreignOverlay.py` | Interface, captura de tela, OCR e atalhos. |
| `nr_logic.py` | Reconhecimento de sinais e lógica das fases. |
| `config.json` | Tempos e preferências do overlay. |
| `INSTALAR.bat` | Instala dependências e gera o executável no Windows. |
| `requirements.txt` | Dependências Python. |
| `test_logic.py` | Testes automatizados da lógica. |
| `icon.ico` | Ícone usado na geração do executável, se estiver presente. |
| `nightreign_overlay.log` | Log criado durante a execução, útil para diagnosticar problemas. |

## 🔧 Solução de problemas

- **O overlay não aparece sobre o jogo:** use *Janela sem bordas* ou modo janela.
- **O OCR não reconhece os avisos:** pressione `F11`, ajuste `regions` no `config.json` e consulte `nightreign_overlay.log`.
- **O instalador falha:** confira a conexão com a internet e a mensagem exibida pelo `INSTALAR.bat`. Caso não encontre um Python compatível, instale o Python 3.12 e execute o instalador novamente.

---

<p align="center"><sub>Projeto independente e não oficial para Elden Ring Nightreign.</sub></p>


## Atualizações: detecção de chefes e posição

- Em instalações novas, o overlay inicia no canto inferior direito. Posições já salvas no `config.json` são preservadas.
- `F6` ativa o modo mover; arraste o overlay e pressione `F6` novamente para salvar a posição.
- A barra de vida é detectada visualmente na parte inferior da tela. Após confirmação em três leituras, o overlay inicia uma fase de combate nos Dias I/II (depois do sinal do 2º círculo ou após 12 minutos de dia, para reduzir detecções de chefes opcionais) ou reinicia o cronômetro de combate do Dia III.
- No Dia III, o cronômetro é encerrado quando a barra deixa de ser detectada por quinze leituras consecutivas. O overlay mantém o tempo final exibido.
- Os atalhos ficam listados no rodapé do overlay.
- `nightreign_boss_catalog.json` reúne os 35 encontros catalogados dos Dias I/II e os 10 Nightlords do Dia III, incluindo confrontos com múltiplos membros.

**Nota sobre a detecção:** o overlay usa análise visual da barra vermelha, não dados internos do jogo. Resolução, efeitos vermelhos e transições de fase podem afetar a detecção; valide em gameplay real. O atraso de quinze leituras reduz encerramentos falsos durante pausas, mas não elimina todas as ambiguidades de barras que somem entre fases.
