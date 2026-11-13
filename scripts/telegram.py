"""Envia ao Telegram as mensagens preparadas em envio/mensagens.json.

Formato: [{"imagem": "envio/eurusd.png" ou null, "texto": "..."}, ...]
Segredos do repositório (GitHub Actions): TELEGRAM_TOKEN e TELEGRAM_CHAT_ID.
Roda no GitHub Actions (o ambiente do Claude não acessa o Telegram).
"""
import json, os, sys, time, re
import urllib.request, urllib.parse, uuid

TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}/"


def limpar(t):
    return re.sub(r"\*\*(.+?)\*\*", r"\1", t).replace("`", "")


def post(metodo, campos, arquivo=None):
    if arquivo:
        b = uuid.uuid4().hex
        corpo = b""
        for k, v in campos.items():
            corpo += f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        nome = os.path.basename(arquivo)
        corpo += (f"--{b}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{nome}\"\r\n"
                  f"Content-Type: image/png\r\n\r\n").encode() + open(arquivo, "rb").read() + f"\r\n--{b}--\r\n".encode()
        req = urllib.request.Request(API + metodo, data=corpo,
                                     headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    else:
        req = urllib.request.Request(API + metodo, data=urllib.parse.urlencode(campos).encode())
    for t in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print(f"  tentativa {t+1} falhou: {e}", file=sys.stderr)
            time.sleep(3 * (t + 1))
    raise RuntimeError(f"falha em {metodo}")


def main():
    if not TOKEN or not CHAT:
        sys.exit("faltam os segredos TELEGRAM_TOKEN e TELEGRAM_CHAT_ID")
    msgs = json.load(open("envio/mensagens.json"))
    for m in msgs:
        texto = limpar(m.get("texto", ""))
        img = m.get("imagem")
        if img and os.path.exists(img):
            legenda = texto.split("\n")[0][:1000]
            post("sendPhoto", {"chat_id": CHAT, "caption": legenda}, img)
            resto = "\n".join(texto.split("\n")[1:]).strip()
        else:
            resto = texto
        for i in range(0, len(resto), 3900):
            post("sendMessage", {"chat_id": CHAT, "text": resto[i:i + 3900], "disable_web_page_preview": "true"})
        time.sleep(1)
    print(f"{len(msgs)} mensagens enviadas")


if __name__ == "__main__":
    main()
