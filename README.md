# Sistema de Turnos · Canchas de Pádel Pablo
**Generado por Gestion-AI · SIGMA**

API REST para gestión de reservas de 4 canchas de pádel con integración ManyChat.

---

## Setup rápido

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear las 4 canchas en la BD
python seed.py

# 3. Iniciar el servidor
python main.py
# → http://localhost:8001
# → Docs: http://localhost:8001/docs
```

---

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/canchas` | Lista las 4 canchas |
| GET | `/canchas/{id}/disponibilidad?fecha=YYYY-MM-DD` | Turnos ocupados de una cancha |
| GET | `/reservas` | Lista reservas (filtros: cancha_id, estado, desde, hasta) |
| POST | `/reservas` | Crear reserva manual |
| PATCH | `/reservas/{id}` | Actualizar estado o notas |
| DELETE | `/reservas/{id}` | Cancelar reserva |
| **POST** | **`/webhook/manychat`** | **Recibir reservas de ManyChat** |
| GET | `/estadisticas/semana` | Stats semanales para el dashboard |

---

## Webhook ManyChat

### URL a configurar en ManyChat:
```
POST http://TU_SERVIDOR:8001/webhook/manychat
```

### Payload que debe enviar ManyChat:
```json
{
  "user_id": "{{user id}}",
  "first_name": "{{first name}}",
  "last_name": "{{last name}}",
  "phone": "{{phone}}",
  "cancha_numero": 2,
  "fecha_str": "2026-04-15 18:00",
  "duracion_minutos": 60
}
```

### Respuesta que devuelve (ManyChat la usa para set_attributes):
```json
{
  "version": "v2",
  "content": {"messages": [{"type": "text", "text": "Reserva confirmada, Juan!..."}]},
  "set_attributes": {
    "reserva_id": "42",
    "reserva_estado": "confirmada",
    "reserva_cancha": "Cancha 2",
    "reserva_hora": "18:00"
  }
}
```

---

## Exponer el servidor públicamente (para ManyChat)

Opciones para desarrollo/testing:
```bash
# Con ngrok (más fácil)
ngrok http 8001
# Copiar la URL pública a ManyChat

# Con cloudflared
cloudflared tunnel --url http://localhost:8001
```

Para producción: deployar en Railway, Render, o VPS con nginx.

---

## Estructura de archivos

```
sistema_turnos/
├── main.py        # FastAPI app + todos los endpoints
├── models.py      # SQLAlchemy: Cancha, Reserva
├── database.py    # Configuración SQLite + sesiones
├── seed.py        # Crea las 4 canchas iniciales
├── requirements.txt
└── README.md
```

Base de datos: `turnos_pablo.db` (SQLite, se crea sola al iniciar)
