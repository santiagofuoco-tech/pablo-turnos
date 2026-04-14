# Guía ManyChat · Canchas de Pádel Pablo

## Resumen de lo que vamos a hacer

| Paso | Qué | Tiempo |
|------|-----|--------|
| 1 | Crear cuenta ManyChat con el mail de Pablo | 5 min |
| 2 | Conectar WhatsApp Business | 15 min |
| 3 | Crear 5 flows de automatización | 20 min |
| 4 | Apuntar webhook al servidor de turnos | 2 min |
| 5 | Prueba final | 5 min |

**URL del servidor de turnos:**
```
https://pablo-turnos-production.up.railway.app
```

**Webhook para ManyChat:**
```
https://pablo-turnos-production.up.railway.app/webhook/manychat
```

---

## PASO 1 · Crear cuenta ManyChat

### 1.1 Ir a ManyChat

1. Abrir: **https://manychat.com**
2. Click en **"Get Started Free"** o **"Sign Up"**
3. Elegir **"Continue with Facebook"**
   - Si Pablo tiene Facebook Business Manager, usarlo
   - Si no, crear cuenta con el mail: `[mail de Pablo]`

### 1.2 Crear el Page (página del negocio)

ManyChat necesita conectarse a una página de Facebook/Instagram o número de WhatsApp.

**Si ya tiene página de Facebook:**
- En el dashboard de ManyChat → "Connect Page"
- Seleccionar la página de Canchas Pádel Pablo

**Si NO tiene página de Facebook:**
- Crear una en **https://www.facebook.com/pages/create**
- Nombre: "Canchas de Pádel Pablo"
- Categoría: "Deportes y Recreación"
- Luego conectar en ManyChat

---

## PASO 2 · Conectar WhatsApp Business

> **Importante:** ManyChat requiere un número de WhatsApp Business API (no el WhatsApp normal).
> El proceso tarda ~15 min y requiere un número de teléfono que NO esté actualmente usando WhatsApp.

### 2.1 Requisitos

- Un número de teléfono (puede ser celular o fijo) que **no tenga WhatsApp activo**
- Si el número de Pablo ya tiene WhatsApp → usar un número nuevo o hacer backup y desvincular

### 2.2 Proceso en ManyChat

1. En el dashboard de ManyChat → menú izquierdo → **"Settings"**
2. → **"Channels"**
3. → Click en **"WhatsApp"**
4. → Click en **"Connect WhatsApp"**

### 2.3 Verificar el número

ManyChat va a pedir:
1. **Nombre del negocio:** Canchas de Pádel Pablo
2. **Número de teléfono:** el número de Pablo (formato +54 9...)
3. **Método de verificación:** elegir SMS o llamada
4. **Ingresar el código** que llega al celular
5. Esperar aprobación (puede tardar unos minutos)

### 2.4 Configurar el perfil de WhatsApp Business

Después de conectar:
- **Nombre del negocio:** Canchas de Pádel Pablo
- **Descripción:** Reservas y consultas de turnos 🎾
- **Dirección:** [dirección de las canchas]
- **Categoría:** Deportes y Recreación
- **Horario:** [horario de atención]

---

## PASO 3 · Importar los flows

### 3.1 Entender la estructura

Tenemos 5 flows definidos en `manychat/flows.json`:

| Flow | Trigger | Qué hace |
|------|---------|---------|
| Consulta disponibilidad | DISPONIBILIDAD, TURNOS, HORARIOS | Muestra horarios libres |
| Reservar turno | RESERVAR, TURNO, QUIERO | Crea reserva en el sistema |
| Cancelar turno | CANCELAR | Cancela por código de reserva |
| FAQ | FAQ, PRECIO, PRECIOS, DONDE | Responde preguntas frecuentes |
| Bienvenida | Primer mensaje / START | Saluda y muestra opciones |

### 3.2 Crear los flows manualmente

> ManyChat no permite importar JSON directamente en el plan gratuito.
> Hay que crearlos desde la UI. Son simples — cada uno tiene 3-5 pasos.

#### Flow 1 · Bienvenida (hacer este primero)

1. En ManyChat → **"Flows"** → **"+ New Flow"**
2. Nombre: `Bienvenida`
3. Click en **"+ Add Trigger"**
   - Tipo: **"Keyword"**
   - Keywords: `HOLA, INICIO, START, MENU`
   - Match type: **"Contains"**
4. Agregar nodo **"Send Message"**:
   ```
   ¡Hola {{first name}}! Bienvenido a las Canchas de Pádel Pablo 🎾

   ¿Qué querés hacer?
   1️⃣ Ver disponibilidad → escribí DISPONIBILIDAD
   2️⃣ Hacer una reserva → escribí RESERVAR
   3️⃣ Cancelar turno → escribí CANCELAR
   4️⃣ Precios y más info → escribí FAQ
   ```
5. Click **"Publish"**

#### Flow 2 · Consulta de disponibilidad

1. **"+ New Flow"** → Nombre: `Consulta disponibilidad`
2. Trigger: Keywords `DISPONIBILIDAD, TURNOS, HORARIOS, CANCHAS`
3. **Send Message:**
   ```
   ¿Para qué día querés consultar disponibilidad?
   Escribí la fecha así: DD/MM (ej: 15/04)
   ```
4. **User Input** → guardar en `consulta_fecha`
5. **Send Message:**
   ```
   ¿Qué cancha te interesa?
   1️⃣ Cancha 1 - Cubierta
   2️⃣ Cancha 2 - Cubierta
   3️⃣ Cancha 3 - Semicubierta
   4️⃣ Cancha 4 - Semicubierta

   Escribí el número (1, 2, 3 o 4)
   ```
6. **User Input** → guardar en `consulta_cancha`
7. **HTTP Request** (ver sección 3.3 abajo)
8. **Send Message:**
   ```
   Para la {{consulta_fecha}} la cancha {{consulta_cancha}} tiene estos turnos ocupados:
   {{disponibilidad_resultado}}

   ¿Querés hacer una reserva? Escribí RESERVAR
   ```
9. Click **"Publish"**

#### Flow 3 · Reservar turno

1. **"+ New Flow"** → Nombre: `Reservar turno`
2. Trigger: Keywords `RESERVAR, TURNO, QUIERO`
3. Pedir nombre completo, fecha, cancha, duración
4. **HTTP Request** al webhook (ver sección 3.3)
5. Mostrar confirmación con código de reserva

#### Flow 4 · Cancelar turno

1. **"+ New Flow"** → Nombre: `Cancelar turno`
2. Trigger: Keywords `CANCELAR`
3. Pedir código de reserva (formato `#123`)
4. **HTTP Request** al backend: `DELETE /reservas/{id}`
5. Confirmar cancelación

#### Flow 5 · FAQ

1. **"+ New Flow"** → Nombre: `FAQ`
2. Trigger: Keywords `FAQ, PRECIO, PRECIOS, DONDE, DIRECCION, CONTACTO`
3. **Send Message:**
   ```
   📍 Canchas de Pádel Pablo
   Dirección: [COMPLETAR CON PABLO]

   💰 Precios:
   • Turno 60 min: $[PRECIO]
   • Turno 90 min: $[PRECIO]

   🕐 Horarios de atención:
   Lunes a Domingo: [HORARIO]

   📞 Contacto directo: [TELÉFONO DE PABLO]
   ```

### 3.3 Configurar el HTTP Request al webhook

Para los flows que necesitan consultar el servidor (Disponibilidad, Reservar):

1. En el flow → agregar nodo **"HTTP Request"** o **"External Request"**
2. Configuración:
   - **Method:** POST
   - **URL:** `https://pablo-turnos-production.up.railway.app/webhook/manychat`
   - **Headers:** `Content-Type: application/json`
   - **Body (JSON):**
     ```json
     {
       "user_id": "{{user_id}}",
       "first_name": "{{first_name}}",
       "last_name": "{{last_name}}",
       "phone": "{{phone}}",
       "cancha_numero": {{cancha_numero}},
       "fecha_str": "{{fecha_str}}",
       "duracion_minutos": 60
     }
     ```
3. En **"Map Response"** → mapear `set_attributes` del response al usuario

---

## PASO 4 · Configurar el webhook de reservas

### 4.1 Webhook principal (el más importante)

Para el flow de reservas, el **HTTP Request** debe ir a:
```
POST https://pablo-turnos-production.up.railway.app/webhook/manychat
```

**Payload esperado por el servidor:**
```json
{
  "user_id": "{{user_id}}",
  "first_name": "{{first_name}}",
  "last_name": "{{last_name}}",
  "phone": "{{phone}}",
  "cancha_numero": 1,
  "fecha_str": "2026-04-20 18:00",
  "duracion_minutos": 60
}
```

**Respuesta del servidor (para ManyChat):**
```json
{
  "version": "v2",
  "content": {
    "messages": [{"type": "text", "text": "Reserva confirmada, Pablo!..."}]
  },
  "set_attributes": {
    "reserva_id": "42",
    "reserva_estado": "confirmada",
    "reserva_cancha": "Cancha 1",
    "reserva_hora": "18:00"
  }
}
```

ManyChat interpreta este formato automáticamente y envía el mensaje al cliente.

### 4.2 Verificar la conexión

Para probar que el webhook funciona desde ManyChat:

1. En el flow → click en el nodo HTTP Request
2. Click en **"Test"** o **"Preview"**
3. ManyChat hace un POST de prueba al endpoint
4. Deberías ver la respuesta con `"reserva_estado": "confirmada"`

---

## PASO 5 · Prueba final

### 5.1 Desde el número de Pablo (como cliente)

1. Abrir WhatsApp en el celular
2. Buscar el número del bot (el que registraste en ManyChat)
3. Mandar: `HOLA`
   - Debe responder con el menú de bienvenida
4. Mandar: `DISPONIBILIDAD`
   - Debe preguntar fecha y cancha, luego mostrar disponibilidad
5. Mandar: `RESERVAR`
   - Completar el flujo → verificar que aparezca un código de reserva
6. Ir a **https://pablo-turnos-production.up.railway.app/reservas**
   - Verificar que la reserva aparece en la lista

### 5.2 Verificar notificación Telegram a Pablo

Cuando se crea la reserva en el paso 5:
- Pablo debe recibir un mensaje en Telegram (del bot PabloCancharBot) con los detalles de la nueva reserva
- Si no llega → verificar que `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` están en Railway

---

## Datos para completar con Pablo

> Estos datos hay que pedirlos en la reunión:

- [ ] **Dirección de las canchas**
- [ ] **Precios por turno (60 min / 90 min)**
- [ ] **Horario de atención**
- [ ] **Teléfono de contacto directo**
- [ ] **¿Tiene Facebook/Instagram Business?**
- [ ] **Número de WhatsApp para el bot** (debe ser distinto al personal si quiere mantener ambos)

---

## Troubleshooting rápido

| Problema | Solución |
|----------|---------|
| ManyChat no conecta WhatsApp | El número ya tiene WhatsApp activo → hacer backup y desvincular primero |
| HTTP Request falla | Verificar que la URL sea exacta con `https://` · Probar en el navegador |
| El bot no responde a keywords | Verificar que el flow esté publicado (Published) y el trigger activo |
| Reserva no aparece en el dashboard | Verificar que el servidor de Railway está corriendo (`/canchas` debe responder) |
| No llega notificación Telegram | Verificar variables `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` en Railway |
