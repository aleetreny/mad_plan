# MadPlan Frontend

Frontend principal de MadPlan construido con React, TypeScript y Vite.

## Comandos

```bash
npm install
npm run dev
npm run build
npm run preview
```

## Smoke test

Desde la raíz del repo:

```bash
python tools/smoke_frontend.py
```

## Estructura

- `src/app`: composición global y SEO.
- `src/domain`: lógica pura de negocio.
- `src/features`: flujos funcionales por dominio de producto.
- `src/shared`: UI y utilidades reutilizables.
