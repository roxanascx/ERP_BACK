# Despliegue del backend en Render

Backend: **FastAPI + MongoDB Atlas** · Repo: `roxanascx/ERP_BACK`

---

## 1. Requisitos previos

- **MongoDB Atlas**: en *Network Access* agregar `0.0.0.0/0` (Allow access from anywhere).
  Render no ofrece IPs fijas en el plan Free, por lo que restringir por IP bloquea la conexión.
- El repo debe estar pusheado a GitHub con los archivos de este commit.

## 2. Crear el servicio en Render

**Opción A — Blueprint (recomendada):** en Render, *New > Blueprint*, seleccionar el repo.
Detecta `render.yaml` y pide solo los valores marcados como secretos.

**Opción B — Manual:** *New > Web Service* y configurar:

| Campo | Valor |
|---|---|
| Language | Python 3 |
| Build Command | `./build.sh` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/health` |

## 3. Variables de entorno

Configurar en *Environment* (o al aplicar el blueprint):

| Variable | Valor | Obligatoria |
|---|---|---|
| `MONGODB_URL` | URI de Atlas (`mongodb+srv://...`) | Sí |
| `DATABASE_NAME` | `web-erp` | Sí |
| `CORS_ORIGINS` | `["https://tu-frontend.vercel.app"]` | Sí |
| `SECRET_KEY` | cadena larga y aleatoria | Sí |
| `DEBUG` | `False` | Sí |
| `ENVIRONMENT` | `production` | Sí |
| `PYTHON_VERSION` | `3.13.3` | Sí |
| `SIRE_FILE_STORAGE` | `/tmp/sire_files` | Recomendada |
| `SUNAT_*` | credenciales SUNAT/SIRE | Opcionales |

`PORT` lo inyecta Render automáticamente: **no definirlo**.

## 4. Verificación post-deploy

```
GET https://<tu-servicio>.onrender.com/health    -> {"status":"healthy",...}
GET https://<tu-servicio>.onrender.com/          -> {"status":"operational",...}
GET https://<tu-servicio>.onrender.com/test-db   -> confirma conexión a Atlas
```

## 5. Puntos a tener en cuenta

- **`/docs` y `/redoc` quedan deshabilitados** con `DEBUG=False`. Para habilitarlos
  temporalmente, poner `DEBUG=True` (expone la API públicamente).
- **Disco efímero**: los archivos en `SIRE_FILE_STORAGE` y los ZIP del PLE se borran en
  cada deploy o reinicio. Para conservarlos hace falta un disco persistente (plan de pago)
  o guardarlos en un bucket externo.
- **Plan Free**: el servicio se duerme tras ~15 min de inactividad; la primera petición
  después tarda ~50 s. El health check de Render no lo mantiene despierto.
- **CORS**: recordar agregar el dominio del frontend a `CORS_ORIGINS` tras desplegarlo.

## 6. Desarrollo local

```bash
cp .env.example .env      # y completar los valores
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```
