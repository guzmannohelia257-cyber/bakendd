# F6 — Offline Flutter

> Esta fase es **100% frontend**. No requiere cambios en el backend.

## Recomendación opcional para el backend
Para idempotencia (cliente reenvía un POST encolado), ver la nota en [F5_offline_web_angular.md](./F5_offline_web_angular.md#recomendación-opcional-para-el-backend). La columna `client_id` se reutiliza para web y mobile.

## Implementación
Ver guía completa de frontend: [G2MOBILE/M8_offline_sqflite.md](../G2MOBILE/M8_offline_sqflite.md)

Incluye:
- SQLite local con `sqflite`
- OutboxService con `connectivity_plus`
- Repository pattern con fallback offline
- Banner UI de estado
- Plan de pruebas manual

## Checklist de cierre F6 (backend)
- [ ] Lo mismo de F5 (columna `client_id` opcional para idempotencia).
- [ ] La implementación frontend está completada (ver M8).
