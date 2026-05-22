"""
Lista endpoints sin summary/tag/response_model.

Reglas:
- Ignora rutas built-in de FastAPI (/openapi.json, /docs, /redoc).
- summary OR docstring/description es suficiente (no requiere ambos).
- Tag es obligatorio.
- response_model recomendado en POST/PUT/PATCH pero solo warning.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


# Rutas internas de FastAPI que no controlamos
SKIP_PATHS = {
    "/openapi.json",
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
}


def main() -> int:
    errores = []      # bloquean
    warnings = []     # informativos
    for route in app.routes:
        if not hasattr(route, "endpoint"):
            continue
        methods = getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
        if not methods:
            continue
        path = route.path
        if path in SKIP_PATHS:
            continue

        summary = getattr(route, "summary", None)
        descripcion = getattr(route, "description", None) or (
            route.endpoint.__doc__ if route.endpoint.__doc__ else None
        )
        tags = getattr(route, "tags", [])
        response_model = getattr(route, "response_model", None)
        method = list(methods)[0]

        problemas_err = []
        problemas_warn = []

        # Documentacion: basta con summary o description
        if not summary and not descripcion:
            problemas_err.append("sin summary NI description/docstring")
        if not tags:
            problemas_err.append("sin tag")

        # response_model solo warning
        if method in ("POST", "PUT", "PATCH") and not response_model:
            problemas_warn.append("sin response_model (warning)")

        if problemas_err:
            errores.append((method, path, problemas_err))
        elif problemas_warn:
            warnings.append((method, path, problemas_warn))

    print(f"\n== AUDITORIA SWAGGER ==")
    print(f"Errores: {len(errores)} | Warnings: {len(warnings)}\n")

    if errores:
        print("ERRORES (deben arreglarse):")
        for m, p, probs in errores:
            print(f"  {m:6s} {p}")
            for x in probs:
                print(f"           - {x}")
        print()

    if warnings:
        print("WARNINGS (recomendado):")
        for m, p, probs in warnings:
            print(f"  {m:6s} {p}")
            for x in probs:
                print(f"           - {x}")
        print()

    if not errores:
        print("OK: no hay errores criticos.")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
