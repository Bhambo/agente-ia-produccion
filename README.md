# 06 — Agente en Producción

> **El producto final.** El agente ya no corre en terminal — corre en un servidor
> y cualquiera puede usarlo desde el navegador.

---

## Cómo correrlo

```bash
# Instala las dependencias nuevas (FastAPI + uvicorn)
pip install -r requirements.txt

# Arranca el servidor
uvicorn main:app --reload

# Abre en el navegador:
# http://localhost:8000
```

---

## Qué incluye

| Archivo | Qué hace |
|---------|----------|
| `main.py` | Servidor FastAPI con 4 endpoints |
| `index.html` | Interfaz de chat en el navegador |
| `requirements.txt` | Dependencias |

**Endpoints:**
- `GET /` → sirve el frontend
- `POST /chat` → recibe mensaje, devuelve respuesta en streaming
- `POST /reset` → limpia el historial
- `GET /health` → comprueba que el servidor vive

---

## Lo nuevo respecto al 04

| Proyecto 04 | Proyecto 06 |
|-------------|-------------|
| Terminal | Navegador web |
| Un usuario (tú) | Cualquiera con el enlace |
| Sin streaming | Letras aparecen en tiempo real |
| Script que se cierra | Servidor que corre siempre |

---

## Para mostrar a un cliente

1. Arranca el servidor: `uvicorn main:app`
2. Abre `http://localhost:8000`
3. Demo en vivo: clima, Wikipedia, notas — todo desde el navegador

Para que el cliente lo use desde su ordenador, el siguiente paso sería desplegarlo en un servidor cloud (Railway, Render, VPS). Eso es el paso natural después de este proyecto.

---

## Estructura

```
06-agente-en-produccion/
├── main.py        ← servidor FastAPI + lógica del agente
├── index.html     ← interfaz de chat
├── requirements.txt
├── README.md
└── notas/         ← se crea automáticamente
```
