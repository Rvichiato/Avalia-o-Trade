# Ligar o TradingView como fonte de dados (feed da Tickmill)

Resultado: a cada candle de 15m fechado, EURUSD, USDJPY e US500 da Tickmill chegam ao repositório em segundos, em `dados/tv/`.

## 1. TradingView (plano Essential ou acima)
1. Ative a autenticação de dois fatores (Perfil → Configurações → Segurança). Sem ela o webhook não funciona.
2. Abra um gráfico de **TICKMILL:EURUSD em 15 minutos**.
3. Editor Pine → cole o conteúdo de `coleta_candles.pine` → Salvar → Adicionar ao gráfico.
4. Nas configurações do indicador, confira os 3 símbolos (se o nome do US500 na Tickmill for outro, escolha pela busca) e troque a **Chave secreta** por uma senha longa sua.
5. Crie o alerta: Condição = "Coleta B&R (webhook)" → **Qualquer chamada da função alert()**. Expiração: a maior possível. Notificações: marque **URL do webhook** e cole o endereço da ponte (passo 2). Mensagem: deixe como está.

## 2. Ponte (Cloudflare Workers, grátis)
1. Crie conta em cloudflare.com → Workers & Pages → Create Worker → cole `ponte_worker.js` → Deploy. Anote o endereço (termina em `.workers.dev`).
2. No Worker → Settings → Variables and Secrets → adicione dois **Secrets**:
   - `SEGREDO`: a mesma chave secreta do passo 1.4;
   - `GITHUB_TOKEN`: no GitHub, Configurações → Developer settings → Personal access tokens → Fine-grained → acesso só ao repositório Avalia-o-Trade, permissão **Contents: Read and write**.

## 3. Teste
Avise o Claude: ele confere se os candles estão chegando em `dados/tv/` e compara com o Yahoo antes de trocar a fonte das análises.
