# Contrato EcoRuta API FastAPI

La base es `http://HOST:8000`; los recursos de negocio usan `/api` y la documentación interactiva está en `/docs`. Todas las respuestas conservan:

```json
{"status": true, "message": "Texto", "data": {}}
```

Los endpoints protegidos reciben `Authorization: Bearer <JWT>`. La API vuelve a consultar que el usuario esté activo y aplica rol y pertenencia del recurso. Errores esperados: 400/422 validación, 401 sesión, 403 autorización, 404 recurso, 409 conflicto/idempotencia, 413 evidencia grande y 5xx temporal.

## Endpoints

| Método y ruta | Rol |
| --- | --- |
| `POST /api/auth/login` | Público |
| `POST`, `DELETE /api/auth/fcm-token` | Autenticado |
| `GET /api/usuario/perfil` | Autenticado |
| `GET /api/puntos` | Autenticado (Catálogo completo de puntos) |
| `POST /api/rutas` | Supervisor (Crear ruta y asignar puntos) |
| `POST /api/rutas/{id}/duplicar` | Supervisor (Duplicar ruta y sus puntos) |
| `GET /api/rutas`, `/api/rutas/{id}`, `/api/rutas/{id}/puntos`, `/api/rutas/{id}/historial` | Según pertenencia |
| `PUT /api/rutas/{id}/asignar` | Supervisor |
| `POST /api/rutas/{id}/iniciar` | Operario asignado |
| `POST /api/rutas/{id}/finalizar` | Operario asignado/Supervisor según regla |
| `POST /api/rutas/{id}/observar`, `/api/rutas/{id}/validar` | Fiscalizador |
| `POST /api/rutas/{id}/reabrir` | Supervisor |
| `GET /api/puntos/{codigo_qr}` | Autenticado según ruta |
| `POST /api/ruta-puntos/{id}/atender`, `/api/ruta-puntos/{id}/incidencias` | Operario asignado |
| `GET /api/rutas/{id}/incidencias`, `/api/incidencias/{id}` | Según pertenencia/rol |
| `PUT /api/incidencias/{id}/estado` | Supervisor/Fiscalizador |
| `GET /api/supervision/resumen` | Supervisor/Fiscalizador |
| `GET /api/usuarios/operarios`, `/api/vehiculos` | Supervisor |
| `GET /uploads/incidencias/{archivo}` | Autenticado y autorizado |

Atención e incidencia requieren UUID v4. El servidor vincula el UUID con autor, recurso y SHA-256 del payload: un replay idéntico no duplica y una reutilización con contenido diferente devuelve 409. La incidencia acepta JSON o `multipart/form-data`, máximo 2 MiB, y valida que la evidencia sea JPEG/PNG real.

`POST /api/rutas/{id}/validar` registra una constancia `CONFORME` sin cambiar `FINALIZADA`; reabrir invalida la revisión vigente. FCM se audita y reintenta después del commit sin revertir la operación principal.

`GET /api/supervision/resumen?fecha=YYYY-MM-DD` devuelve los indicadores operativos para Supervisor (`rutas`, `puntos`, `incidencias` y `avance_general_porcentaje`) y un bloque `fiscalizacion` separado con `pendientes_revision`, `conformes` y `observadas`. Esto permite que ambos roles consulten la misma fuente sin mostrarles el mismo panel funcional.

Para asignar o reasignar, `GET /api/usuarios/operarios` acepta `fecha`, `turno` y el parámetro opcional `excluir_id_ruta`; este último evita que la propia ruta haga aparecer como ocupado a su operario actual.

## Reabrir vs. reprogramar

- **Reabrir** (`POST /api/rutas/{id}/reabrir`) modifica la misma ruta finalizada u observada y la devuelve a `EN_CURSO` para corregir evidencias. Conserva fecha, turno, operario, vehículo y los puntos ya atendidos.
- **Reprogramar** (`POST /api/rutas/{id}/duplicar`) crea una ruta nueva en otra fecha. La nueva ruta queda `PROGRAMADA`, sin asignar operario ni vehículo, copia solo los puntos activos de la ruta origen y los deja `PENDIENTE`. La ruta original permanece intacta.

Body de reprogramación:

```json
{"fecha":"YYYY-MM-DD","turno":"MANANA"}
```

`fecha` es obligatoria, debe usar formato `YYYY-MM-DD` y no puede ser anterior a hoy. `turno` es opcional y válido con `MANANA`, `TARDE` o `NOCHE`; si se omite conserva el turno de la ruta origen.

Respuestas:

- `201`: ruta nueva creada.
- `400`: fecha/turno inválido o fecha pasada.
- `403`: el usuario no tiene rol `SUPERVISOR`.
- `404`: la ruta origen no existe.
- `409`: no quedan puntos activos para copiar o existe conflicto de operario/vehículo.

## Reasignar, reabrir y validación vigente

- `PUT /api/rutas/{id}/asignar` solo reasigna rutas `PROGRAMADA`. Si la ruta no está programada responde `409`.
- `POST /api/rutas/{id}/reabrir` solo acepta rutas `FINALIZADA` u `OBSERVADA`; el comentario es obligatorio. Conserva operario, vehículo y puntos, devuelve la ruta a `EN_CURSO`, invalida la validación vigente y notifica al operario.
- Si el operario asignado ya tiene otra ruta `EN_CURSO`, reapertura responde `409`.
- `GET /api/rutas` y `GET /api/rutas/{id}` incluyen `validada: true|false`, calculado desde una validación fiscal vigente.
