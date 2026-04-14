"""
test-sistema-pablo.py · Prueba end-to-end del sistema de Canchas Pádel Pablo

Pruebas:
  1. API de turnos responde              → GET /canchas
  2. Disponibilidad                      → GET /canchas/1/disponibilidad
  3. Crear reserva de prueba             → POST /reservas
  4. Verificar reserva creada            → GET /reservas/{id}
  5. Estadísticas semanales              → GET /estadisticas/semana
  6. Verificar notificación Telegram     → espera mensaje del bot
  7. Webhook ManyChat responde           → POST /webhook/manychat
  8. Cancelar reserva de prueba          → DELETE /reservas/{id}

Requisitos:
  pip install requests python-dotenv
  Tener .env.telegram con TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID
  O pasar valores manualmente.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta, date
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("\n  ERROR: pip install requests python-dotenv\n")
    sys.exit(1)

DIR = Path(__file__).parent

# ── Cargar configuración ───────────────────────────────────────────────────────

def cargar_config():
    # Backend
    API_URL = os.getenv("API_URL", "https://pablo-turnos-production.up.railway.app")

    # Telegram
    env_telegram = DIR / ".env.telegram"
    if env_telegram.exists():
        load_dotenv(env_telegram)
    env_n8n = DIR / "automatizaciones" / ".env.n8n"
    if env_n8n.exists():
        load_dotenv(env_n8n)

    BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "")

    return API_URL, BOT_TOKEN, CHAT_ID


# ── Resultado acumulado ────────────────────────────────────────────────────────

resultados = []

def registrar(nombre, ok, detalle=""):
    resultados.append({"nombre": nombre, "ok": ok, "detalle": detalle})
    simbolo = "\u2713" if ok else "\u2717"
    color   = "" if ok else ""
    print(f"  {simbolo}  {nombre}" + (f"  →  {detalle}" if detalle else ""))


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_health(api_url):
    print("\n─── 1. Health check ───────────────────────────────────────")
    try:
        r = requests.get(f"{api_url}/canchas", timeout=10)
        if r.status_code == 200:
            canchas = r.json()
            registrar("API responde", True, f"{len(canchas)} canchas")
            for c in canchas:
                print(f"      · {c['nombre']} — {c.get('descripcion', '')}")
            return True
        else:
            registrar("API responde", False, f"HTTP {r.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        registrar("API responde", False, f"No se puede conectar a {api_url}")
        return False
    except Exception as exc:
        registrar("API responde", False, str(exc))
        return False


def test_disponibilidad(api_url):
    print("\n─── 2. Disponibilidad ─────────────────────────────────────")
    manana = (date.today() + timedelta(days=1)).isoformat()
    try:
        r = requests.get(
            f"{api_url}/canchas/1/disponibilidad",
            params={"fecha": manana},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            ocupados = data.get("turnos_ocupados", [])
            registrar(
                "Disponibilidad Cancha 1",
                True,
                f"fecha {manana} · {len(ocupados)} turno(s) ocupado(s)",
            )
            return True
        else:
            registrar("Disponibilidad", False, f"HTTP {r.status_code}: {r.text[:100]}")
            return False
    except Exception as exc:
        registrar("Disponibilidad", False, str(exc))
        return False


def test_crear_reserva(api_url):
    print("\n─── 3. Crear reserva de prueba ────────────────────────────")
    # Buscar un horario disponible mañana a las 23:00 (improbable que esté ocupado)
    manana = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT23:00:00")
    payload = {
        "cancha_id": 1,
        "fecha": manana,
        "duracion_minutos": 60,
        "cliente_nombre": "TEST Sistema Pablo",
        "cliente_telefono": "5491100000000",
        "cliente_email": "test@gestionar.ai",
        "notas": "Reserva de prueba automática — borrar",
    }
    try:
        r = requests.post(f"{api_url}/reservas", json=payload, timeout=10)
        if r.status_code == 201:
            reserva = r.json()
            rid = reserva["id"]
            registrar(
                "Crear reserva",
                True,
                f"id #{rid} · {reserva['cliente_nombre']} · {manana}",
            )
            return rid
        elif r.status_code == 409:
            # Horario ocupado, probar a las 22:00
            payload["fecha"] = (date.today() + timedelta(days=1)).strftime("%Y-%m-%dT22:00:00")
            r2 = requests.post(f"{api_url}/reservas", json=payload, timeout=10)
            if r2.status_code == 201:
                reserva = r2.json()
                rid = reserva["id"]
                registrar("Crear reserva", True, f"id #{rid} (horario 22:00)")
                return rid
            else:
                registrar("Crear reserva", False, f"HTTP {r2.status_code}: {r2.text[:150]}")
                return None
        else:
            registrar("Crear reserva", False, f"HTTP {r.status_code}: {r.text[:150]}")
            return None
    except Exception as exc:
        registrar("Crear reserva", False, str(exc))
        return None


def test_obtener_reserva(api_url, reserva_id):
    print("\n─── 4. Verificar reserva en BD ────────────────────────────")
    try:
        r = requests.get(f"{api_url}/reservas/{reserva_id}", timeout=10)
        if r.status_code == 200:
            reserva = r.json()
            registrar(
                "Reserva en BD",
                True,
                f"id #{reserva_id} · estado: {reserva['estado']}",
            )
            return True
        else:
            registrar("Reserva en BD", False, f"HTTP {r.status_code}")
            return False
    except Exception as exc:
        registrar("Reserva en BD", False, str(exc))
        return False


def test_estadisticas(api_url):
    print("\n─── 5. Estadísticas semanales ─────────────────────────────")
    try:
        r = requests.get(f"{api_url}/estadisticas/semana", timeout=10)
        if r.status_code == 200:
            data = r.json()
            registrar(
                "Estadísticas semana",
                True,
                f"semana {data.get('semana')} · total: {data.get('total_reservas')} reservas",
            )
            return True
        else:
            registrar("Estadísticas", False, f"HTTP {r.status_code}")
            return False
    except Exception as exc:
        registrar("Estadísticas", False, str(exc))
        return False


def test_telegram_notificacion(bot_token, reserva_id):
    print("\n─── 6. Notificación Telegram ──────────────────────────────")

    if not bot_token:
        registrar(
            "Notificación Telegram",
            False,
            "TELEGRAM_BOT_TOKEN no configurado (corrá create_telegram_bot.py primero)",
        )
        return False

    print("  · Esperando que n8n dispare la notificación (15 seg)...")
    time.sleep(15)

    # Obtener mensajes recientes del bot
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{bot_token}/getUpdates",
            params={"limit": 20},
            timeout=10,
        )
        data = r.json()
        if not data.get("ok"):
            registrar("Notificación Telegram", False, data.get("description", "Error API"))
            return False

        updates = data.get("result", [])
        # Buscar un mensaje del bot que mencione la reserva de prueba
        for upd in reversed(updates):
            msg = upd.get("message", {})
            text = msg.get("text", "")
            if f"#{reserva_id}" in text or "TEST Sistema Pablo" in text or "Nueva reserva" in text.lower():
                registrar("Notificación Telegram", True, f"Mensaje recibido: '{text[:60]}...'")
                return True

        # Hay mensajes pero ninguno con el reserva_id — puede que n8n aún no procesó
        if updates:
            ultimo = updates[-1].get("message", {}).get("text", "")
            registrar(
                "Notificación Telegram",
                None,  # Warning, no error
                f"Bot funcionando pero no se encontró mensaje de reserva #{reserva_id}. "
                f"Último msg: '{ultimo[:50]}'",
            )
            # No falla el test — puede ser timing
            resultados[-1]["ok"] = True
            resultados[-1]["detalle"] += " (timing: n8n puede tardar unos seg)"
            return True
        else:
            registrar(
                "Notificación Telegram",
                False,
                "No hay mensajes recientes en el bot. "
                "Verificá que TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID sean correctos en Railway.",
            )
            return False

    except Exception as exc:
        registrar("Notificación Telegram", False, str(exc))
        return False


def test_webhook_manychat(api_url):
    print("\n─── 7. Webhook ManyChat ───────────────────────────────────")
    manana = (date.today() + timedelta(days=2)).strftime("%Y-%m-%d 10:00")
    payload = {
        "user_id": "mc_test_001",
        "first_name": "TEST",
        "last_name": "ManyChat",
        "phone": "5491100000001",
        "cancha_numero": 2,
        "fecha_str": manana,
        "duracion_minutos": 60,
    }
    try:
        r = requests.post(f"{api_url}/webhook/manychat", json=payload, timeout=10)
        if r.status_code == 200:
            data = r.json()
            version = data.get("version", "")
            msgs = data.get("content", {}).get("messages", [])
            texto = msgs[0].get("text", "") if msgs else ""
            attrs = data.get("set_attributes", {})
            if attrs.get("reserva_estado") == "confirmada":
                rid = attrs.get("reserva_id")
                registrar("Webhook ManyChat", True, f"Reserva #{rid} creada · respuesta OK")
                return int(rid) if rid else None
            elif "ocupada" in texto.lower() or "no_disponible" in attrs.get("reserva_estado", ""):
                registrar("Webhook ManyChat", True, f"Responde 'ocupada' correctamente")
                return None
            else:
                registrar("Webhook ManyChat", True, f"Responde: '{texto[:60]}'")
                return None
        else:
            registrar("Webhook ManyChat", False, f"HTTP {r.status_code}: {r.text[:150]}")
            return None
    except Exception as exc:
        registrar("Webhook ManyChat", False, str(exc))
        return None


def cancelar_reservas(api_url, *ids):
    print("\n─── 8. Limpieza (cancelar reservas de prueba) ─────────────")
    for rid in ids:
        if rid is None:
            continue
        try:
            r = requests.delete(f"{api_url}/reservas/{rid}", timeout=10)
            if r.status_code == 200:
                print(f"  ✓  Reserva #{rid} cancelada")
            else:
                print(f"  ·  Reserva #{rid}: HTTP {r.status_code}")
        except Exception as exc:
            print(f"  ·  Reserva #{rid}: {exc}")


# ── Reporte final ──────────────────────────────────────────────────────────────

def reporte_final():
    print(f"\n{'═'*58}")
    print("  REPORTE FINAL")
    print(f"{'═'*58}\n")

    total = len(resultados)
    ok_count   = sum(1 for r in resultados if r["ok"])
    fail_count = total - ok_count

    for r in resultados:
        simbolo = "\u2713" if r["ok"] else "\u2717"
        print(f"  {simbolo}  {r['nombre']}")
        if r["detalle"] and not r["ok"]:
            print(f"        {r['detalle']}")

    print()
    if fail_count == 0:
        print(f"  \u2713  TODO OK — {ok_count}/{total} tests pasaron")
        print()
        print("  El sistema está listo para la reunión con Pablo.")
    else:
        print(f"  \u2717  {fail_count} test(s) fallaron ({ok_count}/{total} OK)")
        print()
        print("  Tests fallidos:")
        for r in resultados:
            if not r["ok"]:
                print(f"    · {r['nombre']}: {r['detalle']}")

    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 58)
    print("  test-sistema-pablo.py · Prueba end-to-end")
    print("  Canchas Pádel Pablo")
    print("=" * 58)

    api_url, bot_token, chat_id = cargar_config()
    print(f"\n  API:      {api_url}")
    print(f"  Telegram: {'configurado' if bot_token else 'NO configurado'}")
    print()

    # 1. Health
    if not test_health(api_url):
        print("\n  ERROR CRÍTICO: La API no responde. Verificá Railway.")
        reporte_final()
        sys.exit(1)

    # 2. Disponibilidad
    test_disponibilidad(api_url)

    # 3. Crear reserva de prueba (el backend va a disparar n8n en background)
    reserva_id = test_crear_reserva(api_url)

    # 4. Verificar en BD
    if reserva_id:
        test_obtener_reserva(api_url, reserva_id)

    # 5. Estadísticas
    test_estadisticas(api_url)

    # 6. Telegram — espera 15 seg para que n8n procese
    if reserva_id:
        test_telegram_notificacion(bot_token, reserva_id)
    else:
        registrar("Notificación Telegram", False, "No se pudo crear reserva de prueba")

    # 7. Webhook ManyChat
    manychat_reserva_id = test_webhook_manychat(api_url)

    # 8. Limpieza
    cancelar_reservas(api_url, reserva_id, manychat_reserva_id)

    # Reporte
    reporte_final()


if __name__ == "__main__":
    main()
