"""Pre-flight check pre-defensa."""
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
        "audit_swagger": step("Swagger audit", [sys.executable, "-m", "scripts.audit_swagger"]),
        "pytest_cov": step(
            "Pytest + cobertura",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/",
                "--cov=app",
                "--cov-report=term-missing",
                "--cov-fail-under=70",
            ],
        ),
        "alembic_check": step("Alembic head check", ["alembic", "current"]),
    }

    print("\n========= RESUMEN =========")
    for name, ok in results.items():
        print(f"  {name:20s} {'OK' if ok else 'FALLO'}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
