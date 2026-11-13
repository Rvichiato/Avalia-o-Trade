// Ponte TradingView -> GitHub (Cloudflare Worker, plano gratuito).
// Variáveis secretas no Worker: SEGREDO (igual à "Chave secreta" do script Pine)
// e GITHUB_TOKEN (token fine-grained só deste repositório, permissão Contents: read and write).
export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") return new Response("ok", { status: 200 });
    let corpo;
    try { corpo = JSON.parse(await request.text()); } catch { return new Response("json inválido", { status: 400 }); }
    if (!corpo || corpo.k !== env.SEGREDO) return new Response("negado", { status: 403 });
    delete corpo.k;
    // responde já (o TradingView cancela após 3 s) e repassa em segundo plano
    ctx.waitUntil(fetch("https://api.github.com/repos/Rvichiato/Avalia-o-Trade/dispatches", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "ponte-tradingview",
      },
      body: JSON.stringify({ event_type: "candle", client_payload: corpo }),
    }));
    return new Response("recebido", { status: 200 });
  },
};
