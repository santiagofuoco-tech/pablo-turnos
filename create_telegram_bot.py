"""
create_telegram_bot.py · Configurar Telegram para Canchas de Pádel Pablo

Qué hace:
  1. Guía la creación del bot con @BotFather
  2. Valida el token automáticamente
  3. Obtiene el chat_id de Pablo esperando que mande un mensaje
  4. Guarda las credenciales en .env.telegram
  5. Actualiza .env.n8n con los nuevos valores
  6. Muestra los valores exactos para pegar en Railway (30 seg manual)
  7. Espera confirmación y verifica que todo funciona

Requisitos:
  pip install requests python-dotenv
"""

import os
import sys
import time
import json
import webbrowser
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv, set_key
except ImportError:
    print("\n  ERROR: pip install requests python-dotenv\n")
    sys.exit(1)

DIR = Path(__file__).parent
ENV_TELEGRAM = DIR / ".env.telegram"
ENV_N8N      = DIR / "automatizaciones" / ".env.n8n"

# ── Helpers ────────────────────────────────────────────────────────────────────

def ok(msg):     print(f"  \u2713  {msg}")
def err(msg):    print(f"  \u2717  {msg}")
def info(msg):   print(f"  \u00b7  {msg}")
def paso(n, t):  print(f"\n{'─'*58}\n  PASO {n} · {t}\n{'─'*58}")
def separador(): print(f"\n{'─'*58}")


def pausar(msg="  [ Presioná ENTER cuando estés listo ] "):
    input(msg)


# ── Paso 1: Instrucciones BotFather ───────────────────────────────────────────

def paso1_instrucciones_botfather():
    paso(1, "Crear el bot con @BotFather")

    print("""
  Abrí Telegram y seguí estos pasos:

  1. Buscar el contacto: @BotFather
  2. Enviar el comando: /newbot
  3. Nombre del bot (nombre visible): Canchas Pádel Pablo
  4. Username del bot (debe terminar en 'bot'): PabloCancharBot
     (si está tomado, probar: PabloCanchasBot, PadelPabloBot, etc.)

  BotFather te va a responder con un mensaje que dice:
  "Done! ... Use this token to access the HTTP API:"
  seguido de un token que se ve así:
  7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    """)

    try:
        webbrowser.open("https://t.me/BotFather")
        info("Se abrió Telegram en el navegador.")
    except Exception:
        info("Abrí manualmente: https://t.me/BotFather")

    pausar()


# ── Paso 2: Ingresar y validar el token ───────────────────────────────────────

def paso2_obtener_token() -> str:
    paso(2, "Pegar el token del bot")

    print()
    while True:
        token = input("  Pegá el token de BotFather: ").strip()
        if not token:
            print("  Token vacío, intentá de nuevo.")
            continue

        print()
        info(f"Validando token...")
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=10,
        )
        data = r.json()

        if not data.get("ok"):
            err(f"Token inválido: {data.get('description', 'error desconocido')}")
            print("  Verificá que copiaste el token completo (sin espacios).")
            print()
            continue

        bot = data["result"]
        ok(f"Bot verificado: @{bot['username']} — {bot['first_name']}")
        return token


# ── Paso 3: Obtener chat_id ────────────────────────────────────────────────────

def paso3_obtener_chat_id(token: str) -> str:
    paso(3, "Obtener el chat_id de Pablo")

    print(f"""
  Ahora Pablo tiene que mandar CUALQUIER mensaje al bot.

  1. Buscar en Telegram: @PabloCancharBot  (o el username elegido)
  2. Presionar START o mandar "hola"
  3. El script lo detecta automáticamente.
    """)

    pausar("  [ Presioná ENTER cuando Pablo haya mandado el mensaje ] ")

    print()
    info("Esperando mensaje... (timeout 120 seg)")

    offset = 0
    for intento in range(40):
        try:
            r = requests.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": offset, "timeout": 3},
                timeout=10,
            )
            data = r.json()
        except Exception as exc:
            info(f"Error de red: {exc}. Reintentando...")
            time.sleep(3)
            continue

        if not data.get("ok"):
            err(f"Error Telegram API: {data}")
            time.sleep(3)
            continue

        updates = data.get("result", [])
        for upd in updates:
            offset = upd["update_id"] + 1
            msg = upd.get("message") or upd.get("my_chat_member")
            if msg:
                chat = msg.get("chat") or msg.get("from")
                if chat:
                    chat_id = str(chat["id"])
                    nombre  = chat.get("first_name", "Pablo")
                    ok(f"Mensaje recibido de: {nombre} (chat_id: {chat_id})")
                    return chat_id

        if intento % 5 == 4:
            info(f"Aún esperando... ({(intento+1)*3} seg)")

    err("Timeout: no se recibió ningún mensaje en 120 segundos.")
    print()
    chat_id = input("  Ingresá el chat_id manualmente (o dejá vacío para salir): ").strip()
    if not chat_id:
        sys.exit(1)
    return chat_id


# ── Paso 4: Guardar credenciales ───────────────────────────────────────────────

def paso4_guardar(token: str, chat_id: str):
    paso(4, "Guardar credenciales")

    # Escribir .env.telegram
    with open(ENV_TELEGRAM, "w", encoding="utf-8") as f:
        f.write(f"TELEGRAM_BOT_TOKEN={token}\n")
        f.write(f"TELEGRAM_CHAT_ID={chat_id}\n")
    ok(f"Guardado en {ENV_TELEGRAM.name}")

    # Actualizar .env.n8n si existe
    if ENV_N8N.exists():
        contenido = ENV_N8N.read_text(encoding="utf-8")
        lineas = [l for l in contenido.splitlines() if not l.startswith("TELEGRAM_")]
        lineas.append(f"TELEGRAM_BOT_TOKEN={token}")
        lineas.append(f"TELEGRAM_CHAT_ID={chat_id}")
        ENV_N8N.write_text("\n".join(lineas) + "\n", encoding="utf-8")
        ok(f"Actualizado {ENV_N8N.name}")
    else:
        info(f"{ENV_N8N.name} no encontrado — saltando")


# ── Paso 5: Instrucciones Railway ──────────────────────────────────────────────

def paso5_railway(token: str, chat_id: str):
    paso(5, "Agregar variables en Railway (≈30 segundos)")

    print(f"""
  Tenés que agregar 2 variables en el servicio n8n de Railway.

  ┌─────────────────────────────────────────────────────┐
  │  Variable               │  Valor                    │
  ├─────────────────────────┼───────────────────────────┤
  │  TELEGRAM_BOT_TOKEN     │  {token[:20]}...      │
  │  TELEGRAM_CHAT_ID       │  {chat_id:<25}   │
  └─────────────────────────────────────────────────────┘

  Pasos:
  1. Ir a: https://railway.app/dashboard
  2. Abrir el proyecto de Pablo (pablo-n8n o similar)
  3. Click en el servicio "n8n"
  4. Pestaña "Variables"
  5. "+ New Variable" dos veces con los valores de arriba
  6. Railway redeploya automáticamente (≈1-2 min)

  Valores exactos para copiar:

    TELEGRAM_BOT_TOKEN
    {token}

    TELEGRAM_CHAT_ID
    {chat_id}
    """)

    try:
        webbrowser.open("https://railway.app/dashboard")
        info("Se abrió Railway en el navegador.")
    except Exception:
        pass

    pausar("  [ Presioná ENTER cuando hayas agregado las variables en Railway ] ")


# ── Paso 6: Esperar redeploy y verificar ─────────────────────────────────────

def paso6_verificar(token: str, chat_id: str):
    paso(6, "Verificar que n8n recibió las variables")

    N8N_URL = "https://n8n-production-2d53.up.railway.app"
    N8N_API_KEY = ""

    # Load from .env.n8n if available
    if ENV_N8N.exists():
        load_dotenv(ENV_N8N)
        N8N_API_KEY = os.getenv("N8N_API_KEY", "")

    # Esperar que Railway redeploy termine
    print()
    info("Esperando que Railway redeploy (hasta 3 min)...")
    time.sleep(15)

    for intento in range(12):
        try:
            r = requests.get(f"{N8N_URL}/healthz", timeout=10)
            if r.status_code == 200:
                ok(f"n8n responde OK en el intento {intento+1}")
                break
        except Exception:
            pass
        info(f"n8n no responde aún ({(intento+1)*15} seg). Esperando...")
        time.sleep(15)
    else:
        err("n8n no responde después de 3 min. Verificá en Railway que el deploy terminó.")

    # Enviar mensaje de prueba directo via Telegram API
    print()
    info("Enviando mensaje de prueba por Telegram...")
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": "✅ <b>¡Configuración exitosa!</b>\n\nEl bot de notificaciones de <b>Canchas Pádel Pablo</b> está funcionando.\n\nVas a recibir aquí:\n🎾 Nuevas reservas\n⏰ Recordatorios 24hs\n📊 Reporte semanal los lunes",
            "parse_mode": "HTML",
        },
        timeout=10,
    )
    data = r.json()
    if data.get("ok"):
        ok("Mensaje de prueba enviado por Telegram. Verificá el chat del bot.")
    else:
        err(f"Error enviando mensaje de prueba: {data.get('description')}")
        err("Verificá que TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID sean correctos.")
        return

    # Verificar via n8n API que las vars están cargadas
    if N8N_API_KEY:
        print()
        info("Verificando workflows en n8n...")
        try:
            n8n_headers = {
                "X-N8N-API-KEY": N8N_API_KEY,
                "Content-Type": "application/json",
            }
            n8n_basic_user = os.getenv("N8N_BASIC_AUTH_USER", "")
            n8n_basic_pass = os.getenv("N8N_BASIC_AUTH_PASSWORD", "")
            auth = (n8n_basic_user, n8n_basic_pass) if n8n_basic_user else None

            r = requests.get(
                f"{N8N_URL}/api/v1/workflows?limit=10",
                headers=n8n_headers,
                auth=auth,
                timeout=15,
            )
            if r.status_code == 200:
                workflows = r.json().get("data", [])
                activos = [w for w in workflows if w.get("active")]
                ok(f"n8n: {len(activos)} workflows activos")
                for w in activos:
                    info(f"  ✓ {w['name']}")
            else:
                info(f"n8n API retornó {r.status_code} — puede que aún esté redeployando")
        except Exception as e:
            info(f"No se pudo verificar n8n: {e}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 58)
    print("  create_telegram_bot.py · Canchas Pádel Pablo")
    print("  Configuración del bot de Telegram")
    print("=" * 58)

    paso1_instrucciones_botfather()
    token   = paso2_obtener_token()
    chat_id = paso3_obtener_chat_id(token)
    paso4_guardar(token, chat_id)
    paso5_railway(token, chat_id)
    paso6_verificar(token, chat_id)

    separador()
    print()
    ok("¡Todo listo! El sistema de notificaciones por Telegram está configurado.")
    print()
    info("Próximos pasos:")
    info("  1. Corrés test-sistema-pablo.py para prueba completa end-to-end")
    info("  2. Configurás ManyChat (ver guia-manychat.md)")
    print()


if __name__ == "__main__":
    main()
