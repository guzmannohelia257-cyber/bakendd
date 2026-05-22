"""Pre-flight para la defensa: corre verificaciones criticas."""
from __future__ import annotations

import subprocess
import sys


def step(name: str, cmd: list[str]) -> bool:
    print(f"\n=== {name} ===")
    result = subprocess.run(cmd)
    ok = result.returncode == 0
    print(f"-> {'OK' if ok else 'FALLO'}")
    return ok


def main() -> int:
    results = {
        "alembic_head": step("Alembic en head", ["alembic", "current"]),
        "seed_demo": step("Seed datos demo", [sys.executable, "-m", "scripts.seed_demo"]),
        "verify_demo": step("Verificar datos", [sys.executable, "-m", "scripts.verify_demo"]),
        "tests": step("Tests pytest", [sys.executable, "-m", "pytest", "tests/", "-q"]),
    }

    print("\n========= PRE-FLIGHT =========")
    for name, ok in results.items():
        print(f"  {name:20s} {'OK' if ok else 'FALLO'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
