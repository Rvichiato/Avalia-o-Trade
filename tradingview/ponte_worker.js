// Ponte TradingView -> GitHub (Cloudflare Worker, plano gratuito).
// Segredos no Worker (Settings -> Variables and Secrets -> tipo "Secret"):
//   SEGREDO       igual à "Chave secreta" do indicador Coleta B&R v2
//   GITHUB_TOKEN  token fine-grained só do repositório Avalia-o-Trade, permissão "Contents: Read and write"
// Teste rápido no navegador: abrir o endereço do Worker deve mostrar "ponte ok".
export default {
  async fetch(request, env, ctx) {
    if (request.method !== "POST") return new Response("ponte ok", { status: 200 });
    let corpo;
    try { corpo = JSON.parse(await request.text()); } catch { return new Response("json inválido", { status: 400 }); }
    if (!corpo || !env.SEGREDO || corpo.k !== env.SEGREDO) return new Response("negado", { status: 403 });
    delete corpo.k;
    corpo.recebido = new Date().toISOString();
    // O TradingView desiste depois de ~3 s: responde já e repassa ao GitHub em segundo plano,
    // com até 3 tentativas se o GitHub falhar.
    ctx.waitUntil((async () => {
      for (let i = 0; i < 3; i++) {
        const r = await fetch("https://api.github.com/repos/Rvichiato/Avalia-o-Trade/dispatches", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
            "Accept": "application/vnd.github+json",
            "User-Agent": "ponte-tradingview",
          },
          body: JSON.stringify({ event_type: "candle", client_payload: corpo }),
        });
        if (r.status < 300) return;
        await new Promise((ok) => setTimeout(ok, 1500 * (i + 1)));
      }
    })());
    return new Response("recebido", { status: 200 });
  },
};
