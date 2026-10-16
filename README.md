# Nightreign Overlay

Overlay leve com o timer das fases do dia de **Elden Ring Nightreign**, sincronizado com o jogo por **leitura de tela (OCR)**. Visual inspirado no jogo, em tons de azul escuro, preto e cinza.

> Projeto de fã, sem afiliação com FromSoftware ou Bandai Namco. O programa **apenas lê a imagem da tela**: não injeta código no jogo nem lê a memória dele. Use por sua conta e risco.

> **Status:** a lógica de fases, a detecção por imagem e a renderização foram testadas em prints reais do jogo. O build do `.exe`, a janela do overlay, os atalhos globais e o Windows OCR ainda precisam de validação em um PC Windows com o jogo.

## Recursos

- Timer por fase do dia (Dia I, II e III), com aparência baseada no conceito do projeto
- Fases mudam **somente por sinais na tela**:

  | Sinal | Fase |
  |---|---|
  | `DAY I/II/III` ou `DIA ...` no centro da tela | Início do dia |
  | "A maré da Noite se fortalece" | 1º círculo começa a fechar |
  | "A chuva se acumula, pressagiando a maré da Noite" | 2º círculo começa a fechar |
  | Barra de vida de um chefe do catálogo | Luta contra o chefe do dia |

- Se o tempo zera e o sinal não apareceu, o timer **conta negativo** até o sinal chegar
- Catálogo de chefes dos dias 1, 2 e 3 (base + DLC *The Forsaken Hollows*) em `data/bosses.json`, em EN e PT-BR. Chefes de campo fora do catálogo são ignorados
- Funciona com o jogo em **português (prioridade)** e inglês
- Arrastável com o mouse; abre no canto inferior direito e lembra a posição
- Atalhos globais exibidos no próprio overlay
- Instalação em um clique; o `.exe` é criado na própria pasta do projeto

## Instalação

Requisitos: Windows 10/11 e internet na primeira instalação.

1. Baixe ou clone o repositório.
2. Execute **`Instalar.bat`**. Ele localiza (ou instala via winget) o Python 3.12, cria um ambiente local `.venv`, instala as dependências e gera `NightreignOverlay.exe` na mesma pasta, com o ícone do projeto.
3. Abra `NightreignOverlay.exe` (ou `Iniciar.bat`).

Se o `.exe` não passar no autoteste, o instalador cria `Nightreign Overlay.lnk`, que roda pelo Python local.

### OCR em português

O Windows precisa do pacote de OCR do idioma: *Configurações > Hora e idioma > Idioma e região > Português (Brasil) > Opções de idioma > Reconhecimento óptico de caracteres*. Sem ele, o overlay mostra "OCR indisponível". Se o Tesseract estiver instalado, é usado como alternativa.

## Atalhos

| Tecla | Ação |
|---|---|
| `F6` | Pausar / retomar |
| `F7` | Resetar (volta a aguardar o Dia I) |
| `F8` | Avançar fase manualmente |
| `F9` | Voltar fase |
| `F10` | Ocultar / mostrar (a leitura de tela também pausa) |
| `F11` | Fechar |

Botão direito no overlay abre o mesmo menu. As teclas são configuráveis em `config.json`.

## Tempos das fases

Dias 1 e 2 (valores de guias da comunidade, ajustáveis em `durations`):

| Fase | Duração | Termina com |
|---|---|---|
| Zona livre | 4:30 | Sinal do 1º círculo |
| 1º círculo fechando | 3:00 | Marco automático por tempo |
| 1º círculo fechado | 3:30 | Sinal do 2º círculo |
| 2º círculo fechando | 3:00 | Barra do chefe |
| Chefe | cronômetro progressivo | Banner do próximo dia |

O Dia 3 é tratado como luta contra o chefe final (cronômetro progressivo). A única troca sem sinal na tela é "1º círculo fechando" para "fechado"; desligue com `"auto_milestone": false`.

## Desempenho

O objetivo principal é não pesar, inclusive em máquinas bem mais fracas que uma RTX 2080 + Ryzen 5 5500:

- Nunca captura a tela inteira: só 3 recortes pequenos, e **apenas o que a fase atual precisa**
- Antes de qualquer OCR, um teste barato de cor/brilho (numpy, cerca de 1 ms) decide se há algo para ler
- Chefe: o OCR lê só a faixa do nome acima da barra de vida; chefes não catalogados fazem as leituras espaçarem sozinhas
- OCR nativo do Windows (sem modelo, sem GPU, sem download)
- Prioridade de processo abaixo do normal
- O overlay é redesenhado apenas quando o texto muda

## Configuração

Tudo em `config.json` (criado na primeira execução):

| Chave | Descrição |
|---|---|
| `scale`, `opacity`, `ui_language` | Tamanho, transparência e idioma do overlay (`pt`/`en`) |
| `regions` | Onde cada texto é lido (fração da tela) |
| `scan` | Intervalos de leitura |
| `signals` | Palavras-chave dos avisos (PT e EN) |
| `durations` | Tempos das fases |
| `hotkeys` | Atalhos |
| `extra_boss_names` | Nomes de chefes adicionais |
| `capture_override` | `[x, y, largura, altura]` para forçar a área capturada |
| `game_process` | Processo do jogo (`nightreign.exe`) |
| `debug` | Grava logs e recortes |

## Testando com um vídeo

1. Coloque o vídeo do YouTube em **tela cheia** no monitor principal (1080p ou mais).
2. Abra o overlay. Sem o jogo aberto, ele captura o monitor inteiro.
3. Vídeo em janela? Defina `capture_override` com a área do vídeo.

Para diagnosticar: `Iniciar_Debug.bat` grava `logs/overlay.log` (texto lido pelo OCR) e recortes em `debug/`. `Testar_Print.bat "print.png"` mostra o que o OCR enxerga em um print.

## Estrutura

```
NightreignOverlay/
├── Instalar.bat          instala e gera o .exe
├── Iniciar.bat / Iniciar_Debug.bat / Testar_Print.bat
├── config.json
├── requirements.txt
├── assets/               moldura (HUD) e ícone
├── data/bosses.json      catálogo de chefes (EN e PT-BR)
├── tools/                gerar_catalogo.py, testar_imagem.py
└── src/
    ├── main.py           entrada (--debug, --selftest)
    ├── ui.py             janela Tkinter, arrastar, menu
    ├── render.py         desenho do overlay (Pillow)
    ├── engine.py         máquina de estados do timer
    ├── scanner.py        thread de leitura da tela
    ├── detect.py         filtros baratos, pré-OCR e interpretação do texto
    ├── ocr.py            Windows OCR (WinRT) com fallback Tesseract
    ├── capture.py        captura de recortes (mss)
    ├── hotkeys.py        atalhos globais
    └── winutil.py        utilidades Win32 (ctypes)
```

## Limitações conhecidas

- Em **tela cheia exclusiva** a captura pode vir preta; use tela cheia sem bordas.
- O OCR pode errar o numeral do dia (I/II/III). O programa aceita direto o dia esperado e exige duas leituras iguais para qualquer outro; `F8`/`F9` corrigem manualmente.
- As frases dos avisos em inglês são estimativas; ajuste `signals` se necessário.
- Nomes de chefes em PT-BR do catálogo incluem traduções de referência, não confirmadas como o texto oficial do jogo. Use `extra_boss_names` para o que o log mostrar.
- Não há detecção do fim do Dia 3; use `F7` para resetar.

## Desenvolvimento

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python src\main.py --debug
```

Regerar o catálogo a partir do `.txt`: `python tools/gerar_catalogo.py catalogo.txt data/bosses.json`.

## Licença

Defina a licença do repositório (por exemplo, MIT). Elden Ring e Nightreign são marcas de seus respectivos titulares.
