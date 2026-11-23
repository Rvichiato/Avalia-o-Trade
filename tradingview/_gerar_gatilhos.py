CAB = {
"nivel": '''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// B&R Nível · alertas de rompimento, reteste e confirmação num nível horizontal
// Ao adicionar ao gráfico (15 minutos), clique no preço do nível. Uma cópia por nível.
// O indicador segue a mesma regra do robô e avisa em cada passo:
//   1) ROMPIMENTO: fechamento além do nível por mais de 0,3 ATR, na direção do modelo;
//   2) RETESTE: o preço volta a tocar o nível pelo outro lado (até 16 candles depois);
//   3) CONFIRMAÇÃO: candle que fecha a favor e do lado certo do nível → entrada no próximo candle,
//      com stop sugerido (atrás do reteste, entre 1,5 e 4 ATR) e o lote que cabe no risco.
//   Falhou: fechou de volta além do nível por mais de 0,3 ATR. Venceu: passou do prazo sem reteste.
// Crie UM alerta por cópia: condição "B&R Nível" → "Qualquer chamada da função alert()", sem expiração.
// ─────────────────────────────────────────────────────────────────────────────
indicator("B&R Nível", overlay = true, max_labels_count = 50)
precoA = input.price(0.0, "Preço do nível", confirm = true)
''',
"linha": '''//@version=6
// ─────────────────────────────────────────────────────────────────────────────
// B&R Linha · alertas de rompimento, reteste e confirmação numa LTA ou LTB
// Ao adicionar ao gráfico (15 minutos), clique nos DOIS apoios da linha (o mais antigo primeiro).
// Uma cópia por linha. Mesma regra do robô:
//   1) ROMPIMENTO: fechamento além da linha por mais de 0,3 ATR, na direção do modelo,
//      só depois do 2º apoio;
//   2) RETESTE: o preço volta a tocar a linha pelo outro lado (até 16 candles depois);
//   3) CONFIRMAÇÃO: candle que fecha a favor e do lado certo → entrada no próximo candle,
//      com stop sugerido (atrás do reteste, entre 1,5 e 4 ATR) e o lote que cabe no risco.
//   Falhou: fechou de volta além da linha por mais de 0,3 ATR. Venceu: passou do prazo sem reteste.
// Crie UM alerta por cópia: condição "B&R Linha" → "Qualquer chamada da função alert()", sem expiração.
// ─────────────────────────────────────────────────────────────────────────────
indicator("B&R Linha", overlay = true, max_labels_count = 50)
tA     = input.time(0, "1º apoio · hora",  confirm = true, inline = "A")
precoA = input.price(0.0, "1º apoio · preço", confirm = true, inline = "A")
tB     = input.time(0, "2º apoio · hora",  confirm = true, inline = "B")
precoB = input.price(0.0, "2º apoio · preço", confirm = true, inline = "B")
''',
}
NIVEL = {
"nivel": '''nivel = precoA
ativo = precoA > 0
nomeGatilho = "nível " + str.tostring(precoA, format.mintick)
''',
"linha": '''inclin = tB != tA ? (precoB - precoA) / (tB - tA) : 0.0
nivel = precoA + inclin * (time - tA)
ativo = precoA > 0 and precoB > 0 and tB > tA and time > tB
tipoLinha = precoB < precoA ? "LTB" : "LTA"
nomeGatilho = tipoLinha + " (hoje em " + str.tostring(nivel, format.mintick) + ")"
''',
}
CORPO = '''
dirIn    = input.string("Automática (tendência do modelo)", "Direção", options = ["Automática (tendência do modelo)", "Venda", "Compra"])
alvoIn   = input.price(0.0, "Alvo (opcional, 0 = sem alvo)")
risco    = input.float(2.0, "Risco por operação (US$)", minval = 0.1, step = 0.5)
rrMin    = input.float(1.5, "Relação mínima alvo/risco", minval = 0.5, step = 0.1)
validade = input.int(16, "Candles para o reteste aparecer", minval = 2)
jaRompido = input.bool(false, "Já foi rompido: esperar só a volta (reteste)", group = "Nível já rompido")
bordaZona = input.price(0.0, "Outro lado da zona (opcional): cancela se fechar além dele", group = "Nível já rompido")
validadeR = input.int(96, "Candles de espera pela volta (96 = 24 h)", minval = 4, group = "Nível já rompido")
bloq     = input.bool(true, "Sem entrada das 10h às 11h (Brasília)")
valorMan = input.float(0.0, "Valor de 1,0 de preço por lote em US$ (0 = automático)", minval = 0.0)

// regra de tendência do robô: 1 alta, -1 baixa, 0 lateral (candles fechados)
tend() =>
    a = ta.sma(ta.tr(true), 14)
    m = ta.sma(close, 60)
    close > m + 0.3 * a and close > close[59] ? 1 : close < m - 0.3 * a and close < close[59] ? -1 : 0
t4 = request.security(syminfo.tickerid, "240", tend()[1], lookahead = barmerge.lookahead_on)
t1 = request.security(syminfo.tickerid, "60",  tend()[1], lookahead = barmerge.lookahead_on)
refT = t4 != 0 ? t4 : t1
dir = dirIn == "Venda" ? -1 : dirIn == "Compra" ? 1 : refT    // -1 venda, 1 compra, 0 nenhuma
nomeDir = dir == -1 ? "VENDA" : dir == 1 ? "COMPRA" : "sem direção"

atr = ta.sma(ta.tr(true), 14)
tol = 0.3 * atr

tk = syminfo.ticker
indice = str.contains(tk, "US500") or str.contains(tk, "SPX")
valorAuto = str.contains(tk, "XAU") ? 100.0 : indice ? 1.0 : str.endswith(tk, "JPY") ? 100000.0 / close : str.endswith(tk, "USD") ? 100000.0 : na
valor = valorMan > 0 ? valorMan : valorAuto

// horário da entrada (abertura do próximo candle), em Brasília
hb = hour(time_close, "America/Sao_Paulo") + minute(time_close, "America/Sao_Paulo") / 60.0
dia = dayofweek(time_close, "America/Sao_Paulo")
util = dia != dayofweek.saturday and dia != dayofweek.sunday
naSessao = util and (indice ? hb >= 11.75 and hb < 18 : hb >= 5 and hb < 19)
naJanela = bloq and util and hb >= 10 and hb < 11

f(x) => str.tostring(x, format.mintick)

// 0 aguardando · 1 rompido · 2 retestado
var int estado = 0
var int barraPasso = 0
var float extremo = na
var bool ladoOk = false
var int dirAtiva = 0
var bool armado = false

if barstate.isconfirmed and ativo and timeframe.period == "15"
    // nível já rompido: a espera do reteste começa no momento em que o indicador é colocado
    if jaRompido and not armado and estado == 0 and dir != 0 and bar_index >= last_bar_index
        if (dir == -1 and close < nivel) or (dir == 1 and close > nivel)
            estado := 1
            barraPasso := bar_index
            dirAtiva := dir
            armado := true
    // para um novo ciclo, o preço precisa ter estado do lado de partida do nível
    if estado == 0 and dir != 0
        if (dir == -1 and close > nivel) or (dir == 1 and close < nivel)
            ladoOk := true
    if estado == 0 and ladoOk and dir != 0
        if (dir == -1 and close < nivel - tol) or (dir == 1 and close > nivel + tol)
            estado := 1
            barraPasso := bar_index
            dirAtiva := dir
            ladoOk := false
            alert(tk + " 15m · 1/3 ROMPIMENTO para " + (dir == -1 ? "baixo" : "cima") + " do " + nomeGatilho + " (a favor: " + nomeDir + "). Agora: esperar o reteste.", alert.freq_once_per_bar_close)
    else if estado >= 1
        d = dirAtiva
        lim = jaRompido and armado and bordaZona > 0 ? bordaZona : nivel
        voltou = (d == -1 and close > lim + tol) or (d == 1 and close < lim - tol)
        if voltou
            alert(tk + " 15m · FALHOU: o preço fechou de volta além do " + nomeGatilho + ". Plano cancelado.", alert.freq_once_per_bar_close)
            estado := 0
            extremo := na
        else if estado == 1 and bar_index - barraPasso > (jaRompido and armado ? validadeR : validade)
            alert(tk + " 15m · VENCEU: passou o prazo sem reteste do " + nomeGatilho + ". Plano cancelado.", alert.freq_once_per_bar_close)
            estado := 0
        else
            toca = (d == -1 and high >= nivel - tol) or (d == 1 and low <= nivel + tol)
            if estado == 1 and toca
                estado := 2
                barraPasso := bar_index
                extremo := d == -1 ? high : low
                alert(tk + " 15m · 2/3 RETESTE do " + nomeGatilho + ". Agora: esperar um candle que feche a favor.", alert.freq_once_per_bar_close)
            if estado == 2
                extremo := d == -1 ? math.max(extremo, high) : math.min(extremo, low)
                confirma = (d == -1 and close < open and close < nivel) or (d == 1 and close > open and close > nivel)
                if confirma
                    entrada = close
                    distBruta = math.abs(extremo - entrada) + 0.1 * atr
                    dist = math.min(math.max(distBruta, 1.5 * atr), 4.0 * atr)
                    stop = entrada - d * dist
                    lote = na(valor) ? na : math.floor(risco / (dist * valor) * 100) / 100
                    rr = alvoIn > 0 ? math.abs(alvoIn - entrada) / dist : na
                    txtAlvo = alvoIn > 0 ? " · alvo " + f(alvoIn) + " = " + str.tostring(rr, "#.#") + "R" + (rr < rrMin ? " (ABAIXO de " + str.tostring(rrMin, "#.#") + "R: não vale)" : "") : " · alvo: antes do 1º obstáculo, mínimo " + str.tostring(rrMin, "#.#") + "R"
                    txtLote = na(lote) ? "" : lote < 0.01 ? " · lote: não cabe em US$ " + str.tostring(risco, "#.##") : " · lote " + str.tostring(lote, "#.##")
                    txtHora = naJanela ? " · ATENÇÃO 10h–11h: NÃO ENTRAR" : not naSessao ? " · FORA DO HORÁRIO: NÃO ENTRAR" : ""
                    alert(tk + " 15m · 3/3 CONFIRMAÇÃO de " + (d == -1 ? "VENDA" : "COMPRA") + " no " + nomeGatilho + ": entrada na abertura do próximo candle (~" + f(entrada) + ") · stop " + f(stop) + txtAlvo + txtLote + txtHora, alert.freq_once_per_bar_close)
                    estado := 0
                    extremo := na
                else if bar_index - barraPasso > validade
                    alert(tk + " 15m · VENCEU: reteste do " + nomeGatilho + " sem confirmação. Plano cancelado.", alert.freq_once_per_bar_close)
                    estado := 0
                    extremo := na

// desenho discreto: a linha do gatilho e um rótulo pequeno à direita, longe dos candles
corLinha = estado == 1 ? color.new(#ffd60a, 0) : estado == 2 ? color.new(#00e5ff, 0) : dir == -1 ? color.new(#ff40a0, 30) : dir == 1 ? color.new(#39ff8c, 30) : color.new(#9aa0b4, 40)
plot(ativo ? nivel : na, "Gatilho", color = corLinha, linewidth = 1, style = plot.style_linebr)
var label rot = na
if barstate.islast and ativo
    label.delete(rot)
    st = timeframe.period != "15" ? "use no gráfico de 15m" : dir == 0 ? "sem direção (4H e 1H laterais)" : estado == 0 ? (jaRompido and not armado ? "esperando o próximo candle para armar" : "aguardando rompimento") : estado == 1 ? (jaRompido and armado ? "já rompido · esperando a volta" : "rompido · esperando reteste") : "retestado · esperando confirmação"
    rot := label.new(bar_index + 4, nivel, nomeDir + " · " + st, style = label.style_label_left, color = color.new(#0b0d18, 20), textcolor = corLinha, size = size.small)
'''
for k in ("nivel", "linha"):
    open(f"gatilho_{k}.pine", "w").write(CAB[k] + NIVEL[k] + CORPO)
print("ok")
