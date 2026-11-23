# TradingView Premium no sistema Break & Retest

Desde 23/11/2026 o TradingView Premium é a fonte principal de preços do robô e o lugar dos alertas.
Tudo aqui usa o feed da **Tickmill** (o mesmo preço em que o Rodrigo opera).

| Peça | Arquivo | O que faz |
|---|---|---|
| Coleta B&R v2 | `coleta_candles.pine` | A cada candle de 15m fechado, manda por webhook os 3 últimos candles de EURUSD, USDJPY, US500 e XAUUSD |
| Ponte | `ponte_worker.js` | Cloudflare Worker grátis: confere a chave secreta e repassa ao GitHub |
| Recebedor | `../scripts/receber.py` + `../.github/workflows/receber.yml` | Grava os candles em `dados/tv/` |
| Robô | `../scripts/sistema.py` | Usa a Tickmill (MT5 + exportação + ponte) quando está em dia; senão, Yahoo de reserva com aviso |
| Saúde da ponte | `../scripts/saude_ponte.py` | Mostra o atraso de cada ativo e qual fonte o robô está usando |
| Painel B&R | `painel_br.pine` | Quadro pequeno no canto: tendência 4H/1H/15m pela regra do robô, direção permitida, sessão, janela 10h–11h, ATR e lote |
| B&R Nível / B&R Linha | `gatilho_nivel.pine`, `gatilho_linha.pine` | Alertas de rompimento → reteste → confirmação num nível ou numa LTA/LTB, com stop e lote |

O que o Premium muda para nós: alertas que **não expiram** (a ponte não para a cada 2 meses), 400 alertas,
webhook, exportação de dados do gráfico, 20 mil candles de histórico, 8 gráficos por aba e Deep Backtesting.

---

## Parte 1 · Ponte de dados (uma vez só, ~20 minutos)

### 1.1 TradingView: segurança
Perfil → Configurações → **Segurança** → ative a **autenticação de dois fatores**. Sem ela o TradingView não envia webhook.

### 1.2 GitHub: token para a ponte
1. github.com → foto → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Nome: `ponte-tradingview` · Expiração: 1 ano · **Repository access: Only select repositories → Avalia-o-Trade**.
3. **Repository permissions → Contents: Read and write** (o resto fica sem acesso).
4. Gere e copie o token (aparece uma vez só). Não mande o token no chat.

### 1.3 Cloudflare: a ponte
1. cloudflare.com → crie a conta grátis → **Workers & Pages** → **Create** → **Create Worker** → nome `ponte-br` → **Deploy**.
2. **Edit code** → apague o que estiver lá → cole todo o `ponte_worker.js` → **Deploy**.
3. No Worker: **Settings → Variables and Secrets → Add** (tipo **Secret**):
   - `SEGREDO`: uma senha longa sua (anote; vai no indicador também);
   - `GITHUB_TOKEN`: o token do passo 1.2.
4. Abra o endereço do Worker (termina em `.workers.dev`) no navegador: deve aparecer **ponte ok**.

### 1.4 TradingView: o coletor
1. Abra um gráfico de **TICKMILL:EURUSD em 15 minutos** (pode ser num layout só para isso).
2. **Pine Editor** → novo indicador → cole `coleta_candles.pine` → **Salvar** → **Adicionar ao gráfico**.
3. Configurações do indicador: confira os 4 ativos (se a Tickmill usar outro nome para o US500 ou o ouro, escolha pela busca) e coloque a **Chave secreta** igual ao `SEGREDO`.
4. **Criar alerta** (ícone do despertador):
   - Condição: **Coleta B&R v2 (webhook)** → **Qualquer chamada da função alert()**;
   - Expiração: **Sem expiração**;
   - Notificações: marque só **URL do webhook** e cole o endereço do Worker (desmarque app/pop-up para não receber aviso a cada 15 min);
   - Nome: `ponte B&R`. Criar.
5. Depois do próximo candle de 15m fechado, avise o Claude: ele confere se chegou em `dados/tv/`.

### 1.5 Tapar o buraco do histórico (uma vez)
O histórico do MT5 vai até 16/11 12h45. Para ligar esse histórico à ponte:
1. Gráfico de **TICKMILL:EURUSD em 15m** → role para trás até o começo de novembro (o Premium guarda 20 mil candles).
2. Menu do gráfico (seta ao lado do nome do layout, no topo) → **Exportar dados do gráfico…** → formato de hora **UNIX** → Exportar.
3. Repita para **USDJPY, US500 e XAUUSD**, sempre em 15m.
4. Mande os 4 arquivos .csv no chat. O Claude importa com `python scripts/importar_tv.py arquivos.csv`.

Enquanto o buraco não for tapado, o robô continua no Yahoo e avisa ("histórico da Tickmill com buraco").

---

## Parte 2 · Alertas do modelo no seu gráfico

### Painel B&R (um por gráfico de 15m)
Pine Editor → cole `painel_br.pine` → salvar → adicionar. Mostra no canto superior direito:
tendência do 4H, 1H e 15m pela regra do robô, a direção que o modelo permite, a sessão e se pode operar agora,
o ATR do 15m e o lote máximo com o stop mínimo. Sombreia de leve das 10h às 11h.
Opcional: alerta "Qualquer chamada da função alert()" avisa quando a direção do modelo muda.

### B&R Nível e B&R Linha (um por gatilho do plano do dia)
- **Nível:** adicionar ao gráfico de 15m → clicar no preço do nível.
- **Linha (LTA/LTB):** adicionar → clicar no 1º apoio e depois no 2º apoio.
- Nas configurações: direção (automática pela tendência, ou fixa), **alvo** do plano (para o alerta dizer quantos R dá) e risco (US$ 2).
- Criar alerta: condição **B&R Nível** (ou **B&R Linha**) → **Qualquer chamada da função alert()** → **Sem expiração** → notificação no **app** (e e-mail se quiser).

Você recebe no celular:
1. **1/3 ROMPIMENTO** – fechou além do nível por mais de 0,3 ATR, a favor do modelo. Esperar o reteste.
2. **2/3 RETESTE** – voltou a tocar o nível pelo outro lado. Esperar a confirmação.
3. **3/3 CONFIRMAÇÃO** – entrada na abertura do próximo candle, com stop sugerido, lote e R do alvo.
   Se for das 10h às 11h ou fora da sessão, o próprio alerta diz **NÃO ENTRAR**.
- **FALHOU** (fechou de volta além do nível) ou **VENCEU** (16 candles sem reteste/confirmação): plano cancelado.

As análises das 05h20 e 11h45 dizem exatamente onde colocar cada Nível/Linha e o alvo.
Apague os gatilhos do dia anterior para não acumular (o Premium aceita 400 alertas, mas a tela fica poluída).

---

## Parte 3 · Layout sugerido (8 gráficos por aba)
- **Aba "Mesa"** (grade 2 × 4): na linha de cima o 15m de EURUSD, USDJPY, US500 e XAUUSD; na de baixo o 4H dos mesmos.
  Painel B&R em todos os de 15m.
- **Uma aba por ativo** (3 gráficos: 4H, 1H e 15m), com **símbolo e cruz sincronizados**. É onde ficam as suas linhas e os gatilhos.
- **Aba "Ponte"**: só o EURUSD 15m com o Coleta B&R v2. Não precisa ficar aberta: o alerta roda nos servidores do TradingView.

## Parte 4 · Se algo parar
- `python scripts/saude_ponte.py` mostra o atraso de cada ativo e a fonte em uso.
- No TradingView, **Alertas → Registro**: cada disparo da ponte aparece ali; erro de webhook também.
- No GitHub, **Actions → "Receber candles do TradingView"**: uma execução a cada 15 min em mercado aberto.
- No Cloudflare, **Workers → ponte-br → Logs**: chamadas recebidas e respostas (403 = chave secreta diferente).
