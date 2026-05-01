# Fénix Legal — Frontend v2.5

Motor RAG jurídico con verificación automática de citas.

## Stack

- **React 18** + **TypeScript** + **Vite**
- **Tailwind CSS** — paleta prestige/surface/accent/line
- **Framer Motion** — animaciones y transiciones
- **sse-starlette** — streaming SSE nativo del backend
- **react-pdf** — visor de documentos PDF
- **sonner** — notificaciones toast

## Arquitectura de integración

```
Frontend (puerto 3000)
    │
    ├── POST /api/v2/stream     → SSE streaming (chat principal)
    ├── POST /api/v2/query      → Query síncrona (fallback)
    ├── GET  /api/v2/health     → Health check
    ├── POST /api/process-pdf   → Upload de documentos
    └── POST /api/vectorize     → Indexación vectorial
         │
         ▼
    Backend FastAPI (puerto 8000)
    Fénix Legal v2.5 — Fase 3
```

## Eventos SSE consumidos

| Evento | Descripción |
|--------|-------------|
| `token` | Fragmento de texto en tiempo real |
| `verification_start` | Inicio de verificación de citas |
| `verification_complete` | Resultado de la verificación |
| `final_response` | `LegalAnswerResponse` completo |
| `error` | Error con `error_id` trazable |
| `heartbeat` | Keepalive (ignorado por el cliente) |

## Instalación y desarrollo

### Prerrequisitos
- Node.js >= 18
- Backend Fénix Legal corriendo en `http://localhost:8000`

### Instalar dependencias

```bash
npm install
```

### Variables de entorno

Crear `.env.local`:
```
BACKEND_URL=http://localhost:8000
PORT=3000
```

### Desarrollo

```bash
# Iniciar frontend (proxy automático al backend)
npm run dev

# El backend debe estar corriendo:
cd ../backend && uvicorn api.main:app --reload --port 8000
```

### Producción

```bash
npm run build
# El bundle generado en dist/ es servido directamente por FastAPI
# Ver api/main.py — endpoint estático en producción
```

## Estructura del proyecto

```
src/
├── api/
│   └── client.ts          # Cliente REST (query síncrona, upload, vectorize)
├── components/
│   └── Dashboard.tsx      # Componente principal — layout completo
├── hooks/
│   └── useStream.ts       # Hook SSE — consume /api/v2/stream
├── types/
│   └── index.ts           # Tipos alineados con LegalAnswerResponse v2
├── App.tsx
└── main.tsx

server.ts                  # Dev server con proxy a FastAPI
```

## Cambios respecto al template original

| Aspecto | Template (Gemini) | Fénix Legal v2.5 |
|---------|-------------------|------------------|
| LLM | Google Gemini API (cliente) | Backend FastAPI — Bedrock |
| Streaming | `generateContentStream` | SSE nativo `/api/v2/stream` |
| Tipos | `Message`, `DocumentInfo` genéricos | `LegalAnswerResponse`, `CitationOut`... |
| Verificación | ❌ | ✅ Citation Verifier + Numeric Grader |
| Citas | ❌ | ✅ Panel expandible por mensaje |
| Discrepancias | ❌ | ✅ Badges por tipo numérico |
| Confianza | ❌ | ✅ `confidence_score` badge |
| Fases SSE | ❌ | ✅ generating → verifying → complete |
| Server | Mock endpoints | Proxy transparente a FastAPI |
