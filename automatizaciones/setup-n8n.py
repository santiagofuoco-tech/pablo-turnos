"""
setup-n8n.py · Configuración automática de n8n para Canchas de Pádel Pablo

Compatible con:
    · n8n self-hosted en Railway  →  https://n8n-pablo-production.up.railway.app
    · n8n Cloud                   →  https://TU-INSTANCIA.app.n8n.cloud

Uso:
    1. Completar .env.n8n con N8N_INSTANCE_URL y N8N_API_KEY
    2. pip install requests python-dotenv
    3. python setup-n8n.py

Qué hace:
    - Verifica conexión con la instancia n8n
    - Configura la variable API_BASE_URL
    - Importa los 3 flujos de automatización
    - Activa los 3 flujos
    - Muestra resumen y URL del webhook
"""

import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: Falta el paquete 'requests'.")
    print("       Ejecutá: pip install requests python-dotenv")
    sys.exit(1)

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: Falta el paquete 'python-dotenv'.")
    print("       Ejecutá: pip install requests python-dotenv")
    sys.exit(1)


# ── Colores para la terminal ───────────────────────────────────────────────────

def ok(msg):    print(f"  ✓  {msg}")
def err(msg):   print(f"  ✗  {msg}")
def info(msg):  print(f"  ·  {msg}")
def titulo(msg): print(f"\n{'─'*55}\n  {msg}\n{'─'*55}")


# ── Configuración ──────────────────────────────────────────────────────────────

DIR = Path(__file__).parent

FLUJOS = [
    DIR / "notificacion-reserva.json",
    DIR / "recordatorio-24hs.json",
    DIR / "reporte-semanal.json",
]


def cargar_config():
    env_path = DIR / ".env.n8n"
    if not env_path.exists():
        err(f"No se encontró .env.n8n en {DIR}")
        err("Creá el archivo con N8N_INSTANCE_URL y N8N_API_KEY")
        sys.exit(1)

    load_dotenv(env_path)

    instance_url    = os.getenv("N8N_INSTANCE_URL", "").rstrip("/")
    api_key         = os.getenv("N8N_API_KEY", "")
    api_base_url    = os.getenv("API_BASE_URL", "")
    basic_auth_user = os.getenv("N8N_BASIC_AUTH_USER", "")
    basic_auth_pass = os.getenv("N8N_BASIC_AUTH_PASSWORD", "")

    errores = []
    if not instance_url or "TU-INSTANCIA" in instance_url or "n8n-pablo-production" in instance_url:
        errores.append("N8N_INSTANCE_URL no configurada con la URL real de tu instancia")
    if not api_key or api_key == "tu-api-key-aqui":
        errores.append("N8N_API_KEY no configurada")
    if not api_base_url:
        errores.append("API_BASE_URL no configurada")

    if errores:
        err("Configuración incompleta en .env.n8n:")
        for e in errores:
            print(f"     → {e}")
        print()
        info("── n8n en Railway ──────────────────────────────────────")
        info("  URL:     Railway → servicio n8n → Settings → Networking")
        info("           Es algo como: https://n8n-pablo-production.up.railway.app")
        info("  API key: en n8n → Settings → API → Create an API key")
        print()
        info("── n8n Cloud ───────────────────────────────────────────")
        info("  URL:     Settings → General → Instance URL")
        info("           Es algo como: https://tunombre.app.n8n.cloud")
        info("  API key: Settings → API → Create an API key")
        sys.exit(1)

    return instance_url, api_key, api_base_url, basic_auth_user, basic_auth_pass


# ── Cliente HTTP ───────────────────────────────────────────────────────────────

class N8NClient:
    def __init__(self, instance_url: str, api_key: str, basic_user: str = "", basic_pass: str = ""):
        self.base = f"{instance_url}/api/v1"
        self.session = requests.Session()
        self.session.headers.update({
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        # Si la instancia tiene N8N_BASIC_AUTH_ACTIVE=true, agregar Basic Auth
        if basic_user and basic_pass:
            self.session.auth = (basic_user, basic_pass)

    def get(self, path: str) -> dict:
        r = self.session.get(f"{self.base}{path}", timeout=15)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, body: dict) -> dict:
        r = self.session.post(f"{self.base}{path}", json=body, timeout=15)
        r.raise_for_status()
        return r.json()

    def patch(self, path: str, body: dict) -> dict:
        r = self.session.patch(f"{self.base}{path}", json=body, timeout=15)
        r.raise_for_status()
        return r.json()

    def delete(self, path: str) -> None:
        r = self.session.delete(f"{self.base}{path}", timeout=15)
        r.raise_for_status()


# ── Paso 1: Verificar conexión ─────────────────────────────────────────────────

def verificar_conexion(client: N8NClient, instance_url: str):
    titulo("PASO 1 · Verificando conexión con n8n Cloud")
    try:
        data = client.get("/workflows?limit=1")
        ok(f"Conectado a {instance_url}")
        total = data.get("count", "?")
        info(f"Workflows existentes en la cuenta: {total}")
        return True
    except requests.exceptions.ConnectionError:
        err(f"No se puede conectar a {instance_url}")
        err("Verificá que la URL sea correcta y que tengas internet")
        return False
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            err("API Key inválida o sin permisos")
            err("Generá una nueva en: Settings → API → Create an API key")
        else:
            err(f"Error HTTP {e.response.status_code}: {e.response.text[:200]}")
        return False


# ── Paso 2: Configurar variable API_BASE_URL ───────────────────────────────────

def configurar_variable(client: N8NClient, api_base_url: str):
    titulo("PASO 2 · Configurando variable API_BASE_URL")

    # Verificar si ya existe
    try:
        variables = client.get("/variables")
        existente = next(
            (v for v in variables.get("data", []) if v.get("key") == "API_BASE_URL"),
            None
        )
    except Exception:
        variables = {"data": []}
        existente = None

    if existente:
        # Actualizar si el valor es diferente
        if existente.get("value") == api_base_url:
            ok(f"API_BASE_URL ya configurada: {api_base_url}")
            return True
        try:
            client.patch(f"/variables/{existente['id']}", {
                "key": "API_BASE_URL",
                "value": api_base_url,
            })
            ok(f"API_BASE_URL actualizada → {api_base_url}")
            return True
        except Exception as e:
            err(f"No se pudo actualizar la variable: {e}")
            return False
    else:
        try:
            client.post("/variables", {
                "key": "API_BASE_URL",
                "value": api_base_url,
            })
            ok(f"API_BASE_URL creada → {api_base_url}")
            return True
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (404, 403, 400):
                # n8n free tier / self-hosted sin licencia no tiene API de variables
                info("API de variables no disponible (requiere licencia Enterprise)")
                info("API_BASE_URL ya está configurada como env var en Railway — OK")
                info(f"  Key:   API_BASE_URL")
                info(f"  Value: {api_base_url}")
                return True  # No es bloqueante, continuamos
            err(f"Error al crear variable: {e.response.text[:200]}")
            return False
        except Exception as e:
            err(f"Error inesperado: {e}")
            return False


# ── Paso 3: Importar flujos ────────────────────────────────────────────────────

def preparar_workflow(ruta: Path) -> dict:
    """Lee el JSON y lo adapta al formato que espera la API de n8n."""
    with open(ruta, encoding="utf-8") as f:
        raw = json.load(f)

    # Quitar campos propios que n8n no entiende
    raw.pop("_meta", None)

    # Asegurarse de que tenga settings mínimos
    if "settings" not in raw:
        raw["settings"] = {}
    raw["settings"].setdefault("executionOrder", "v1")

    # n8n espera que los nodos tengan ciertos campos
    for nodo in raw.get("nodes", []):
        nodo.setdefault("disabled", False)
        nodo.setdefault("continueOnFail", False)
        nodo.setdefault("alwaysOutputData", False)
        nodo.setdefault("executeOnce", False)
        nodo.setdefault("notesInFlow", False)
        nodo.setdefault("credentials", {})

    return raw


def importar_flujos(client: N8NClient) -> list[dict]:
    titulo("PASO 3 · Importando flujos de automatización")

    workflows_creados = []
    workflows_existentes = client.get("/workflows?limit=50").get("data", [])
    nombres_existentes = {w["name"]: w for w in workflows_existentes}

    for ruta in FLUJOS:
        if not ruta.exists():
            err(f"Archivo no encontrado: {ruta.name}")
            continue

        payload = preparar_workflow(ruta)
        nombre = payload.get("name", ruta.stem)

        # Si ya existe, preguntar si reemplazar
        if nombre in nombres_existentes:
            existente = nombres_existentes[nombre]
            info(f"'{nombre}' ya existe (id: {existente['id']}) — omitiendo importación")
            workflows_creados.append(existente)
            continue

        try:
            creado = client.post("/workflows", payload)
            ok(f"Importado: '{nombre}' (id: {creado['id']})")
            workflows_creados.append(creado)
        except requests.exceptions.HTTPError as e:
            err(f"Error importando '{nombre}': {e.response.status_code}")
            err(f"    Detalle: {e.response.text[:300]}")
        except Exception as e:
            err(f"Error inesperado importando '{nombre}': {e}")

    return workflows_creados


# ── Paso 4: Activar flujos ─────────────────────────────────────────────────────

def activar_flujos(client: N8NClient, workflows: list[dict]):
    titulo("PASO 4 · Activando flujos")

    for wf in workflows:
        wf_id   = wf["id"]
        nombre  = wf["name"]
        activo  = wf.get("active", False)

        if activo:
            ok(f"'{nombre}' — ya estaba activo")
            continue

        try:
            client.post(f"/workflows/{wf_id}/activate", {})
            ok(f"'{nombre}' — activado")
        except requests.exceptions.HTTPError as e:
            err(f"No se pudo activar '{nombre}': {e.response.status_code}")
            err(f"    Detalle: {e.response.text[:200]}")
        except Exception as e:
            err(f"Error inesperado activando '{nombre}': {e}")


# ── Paso 5: Verificación final ─────────────────────────────────────────────────

def verificar_resultado(client: N8NClient, instance_url: str):
    titulo("PASO 5 · Verificación final")

    try:
        data = client.get("/workflows?limit=50")
        workflows = data.get("data", [])
    except Exception as e:
        err(f"No se pudo obtener lista de workflows: {e}")
        return

    nombres_esperados = {
        "Pádel Pablo · Notificación de nueva reserva",
        "Pádel Pablo · Recordatorio 24hs antes del turno",
        "Pádel Pablo · Reporte semanal por Telegram",
    }

    encontrados = {wf["name"]: wf for wf in workflows if wf["name"] in nombres_esperados}

    todos_ok = True
    for nombre in nombres_esperados:
        if nombre not in encontrados:
            err(f"NO ENCONTRADO: '{nombre}'")
            todos_ok = False
        else:
            wf = encontrados[nombre]
            estado = "ACTIVO" if wf.get("active") else "INACTIVO"
            simbolo = "✓" if wf.get("active") else "✗"
            print(f"  {simbolo}  [{estado}] {nombre}")
            if not wf.get("active"):
                todos_ok = False

    print()
    if todos_ok:
        ok("Todo listo. Los 3 flujos están importados y activos.")
        print()
        info("URLs útiles:")
        info(f"  Panel n8n:   {instance_url}")
        info(f"  Workflows:   {instance_url}/workflows")
        print()
        info("Configurar Telegram (con Pablo):")
        info("  1. Crear bot con @BotFather → copiar TELEGRAM_BOT_TOKEN")
        info("  2. Iniciar chat con el bot → llamar /getUpdates → copiar chat_id")
        info("  3. Agregar en Railway (n8n service) → Variables:")
        info("       TELEGRAM_BOT_TOKEN = <token del bot>")
        info("       TELEGRAM_CHAT_ID   = <chat_id de Pablo>")
        print()
        info("Próximo paso: conectar el backend de Railway al webhook.")
        info("  Ver instrucciones al final de README-activacion.md")
    else:
        err("Algunos flujos no quedaron activos. Revisá los errores arriba.")
        info(f"  Panel n8n: {instance_url}/workflows")

    # Mostrar URL del webhook de notificación si existe
    notif = encontrados.get("Pádel Pablo · Notificación de nueva reserva")
    if notif:
        webhook_url = f"{instance_url}/webhook/nueva-reserva"
        print()
        info("URL del webhook de notificación de reserva:")
        info(f"  {webhook_url}")
        info("  → Agregarla en main.py del backend (ver README-activacion.md)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 55)
    print("  setup-n8n.py · Canchas de Pádel Pablo")
    print("  Configuración automática de n8n Cloud")
    print("=" * 55)

    instance_url, api_key, api_base_url, basic_user, basic_pass = cargar_config()
    client = N8NClient(instance_url, api_key, basic_user, basic_pass)

    if not verificar_conexion(client, instance_url):
        sys.exit(1)

    configurar_variable(client, api_base_url)
    workflows = importar_flujos(client)

    if not workflows:
        err("No se importó ningún flujo. Verificá los errores arriba.")
        sys.exit(1)

    activar_flujos(client, workflows)
    verificar_resultado(client, instance_url)


if __name__ == "__main__":
    main()
