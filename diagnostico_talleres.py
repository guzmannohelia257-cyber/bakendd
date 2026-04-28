"""
Diagnostico del motor de asignacion:
- Estado de todos los talleres (verificado, disponible, coordenadas)
- Categorias que atiende cada taller
- Tecnicos vinculados por taller
- Como quedarian los candidatos para cada categoria
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/yary")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def sep(titulo=""):
    print("\n" + "=" * 70)
    if titulo:
        print(f"  {titulo}")
        print("=" * 70)


def run():
    db = SessionLocal()
    try:
        sep("1. ESTADO DE TODOS LOS TALLERES")
        rows = db.execute(text("""
            SELECT
                t.id_taller,
                t.nombre,
                t.activo,
                t.verificado,
                t.disponible,
                t.latitud IS NOT NULL AS tiene_lat,
                t.longitud IS NOT NULL AS tiene_lon,
                t.capacidad_max,
                t.latitud,
                t.longitud
            FROM taller t
            ORDER BY t.id_taller
        """)).fetchall()

        if not rows:
            print("  ADVERTENCIA: No hay talleres en la base de datos.")
        else:
            print(f"  {'ID':>3}  {'Nombre':<25}  {'Act':^3}  {'Ver':^3}  {'Dis':^3}  {'Coords':^6}  {'Cap':^3}  {'Lat / Lon':<25}  Motor")
            print("  " + "-" * 95)
            for r in rows:
                coords_ok = "SI" if r.tiene_lat and r.tiene_lon else "NO"
                lat_lon = f"{r.latitud:.4f}, {r.longitud:.4f}" if r.tiene_lat and r.tiene_lon else "---"
                pasa_motor = "PASA" if r.activo and r.verificado and r.disponible and r.tiene_lat and r.tiene_lon else "EXCLUIDO"
                print(
                    f"  {r.id_taller:>3}  {r.nombre:<25}  "
                    f"{'SI' if r.activo else 'NO':^3}  "
                    f"{'SI' if r.verificado else 'NO':^3}  "
                    f"{'SI' if r.disponible else 'NO':^3}  "
                    f"{coords_ok:^6}  "
                    f"{r.capacidad_max:^3}  "
                    f"{lat_lon:<25}  {pasa_motor}"
                )

        sep("2. CATEGORIAS QUE ATIENDE CADA TALLER (taller_servicio)")
        rows = db.execute(text("""
            SELECT
                t.id_taller,
                t.nombre AS taller,
                t.verificado,
                cp.nombre AS categoria,
                ts.servicio_movil
            FROM taller_servicio ts
            JOIN taller t ON t.id_taller = ts.id_taller
            JOIN categoria_problema cp ON cp.id_categoria = ts.id_categoria
            ORDER BY t.id_taller, cp.nombre
        """)).fetchall()

        if not rows:
            print("  ADVERTENCIA: No hay registros en taller_servicio. El motor no encontrara candidatos.")
        else:
            taller_actual = None
            for r in rows:
                if r.taller != taller_actual:
                    verif = "verificado=SI" if r.verificado else "verificado=NO (motor lo excluira)"
                    print(f"\n  Taller #{r.id_taller} --- {r.taller}  ({verif})")
                    taller_actual = r.taller
                movil = "movil" if r.servicio_movil else "solo taller"
                print(f"    - {r.categoria:<15} ({movil})")

        sep("3. TECNICOS VINCULADOS POR TALLER (usuario_taller)")
        rows = db.execute(text("""
            SELECT
                t.id_taller,
                t.nombre AS taller,
                u.nombre AS tecnico,
                u.activo AS u_activo,
                ut.activo AS ut_activo,
                ut.disponible
            FROM usuario_taller ut
            JOIN taller t ON t.id_taller = ut.id_taller
            JOIN usuario u ON u.id_usuario = ut.id_usuario
            ORDER BY t.id_taller, u.nombre
        """)).fetchall()

        if not rows:
            print("  ADVERTENCIA: No hay tecnicos vinculados. El score de disponibilidad sera 0 para todos.")
        else:
            taller_actual = None
            for r in rows:
                if r.taller != taller_actual:
                    print(f"\n  Taller #{r.id_taller} --- {r.taller}")
                    taller_actual = r.taller
                disp = "DISPONIBLE" if r.ut_activo and r.disponible and r.u_activo else "NO disponible"
                print(f"    - {r.tecnico:<20} {disp}")

        sep("4. SIMULACION: TALLERES QUE PASAN EL FILTRO DEL MOTOR POR CATEGORIA")
        categorias = db.execute(text(
            "SELECT id_categoria, nombre FROM categoria_problema ORDER BY id_categoria"
        )).fetchall()

        for cat in categorias:
            candidatos = db.execute(text("""
                SELECT
                    t.id_taller,
                    t.nombre,
                    t.verificado,
                    t.disponible,
                    t.activo,
                    t.latitud IS NOT NULL AND t.longitud IS NOT NULL AS tiene_coords
                FROM taller t
                JOIN taller_servicio ts ON ts.id_taller = t.id_taller
                WHERE ts.id_categoria = :cat_id
                ORDER BY t.id_taller
            """), {"cat_id": cat.id_categoria}).fetchall()

            aptos = [r for r in candidatos if r.activo and r.verificado and r.disponible and r.tiene_coords]
            total = len(candidatos)
            aptos_n = len(aptos)

            if aptos_n == 0:
                icono = "[SIN CANDIDATOS]"
            elif aptos_n == 1:
                icono = "[SOLO 1 - PROBLEMA]"
            else:
                icono = f"[OK - {aptos_n} candidatos]"

            print(f"\n  {icono} Categoria '{cat.nombre}' (id={cat.id_categoria}): {aptos_n}/{total} pasan el motor")
            for r in candidatos:
                pasa = r.activo and r.verificado and r.disponible and r.tiene_coords
                razon = []
                if not r.activo:     razon.append("activo=NO")
                if not r.verificado: razon.append("verificado=NO")
                if not r.disponible: razon.append("disponible=NO")
                if not r.tiene_coords: razon.append("sin coordenadas")
                estado = "PASA" if pasa else f"EXCLUIDO ({', '.join(razon)})"
                print(f"      #{r.id_taller} {r.nombre:<25} -> {estado}")

        sep("5. ULTIMOS 10 INCIDENTES Y SUS CANDIDATOS GUARDADOS")
        rows = db.execute(text("""
            SELECT
                i.id_incidente,
                cp.nombre AS categoria,
                ei.nombre AS estado,
                COUNT(ca.id_candidato) AS n_candidatos,
                STRING_AGG(t.nombre, ', ' ORDER BY ca.score_total DESC) AS talleres
            FROM incidente i
            LEFT JOIN categoria_problema cp ON cp.id_categoria = i.id_categoria
            LEFT JOIN estado_incidente ei ON ei.id_estado = i.id_estado
            LEFT JOIN candidato_asignacion ca ON ca.id_incidente = i.id_incidente
            LEFT JOIN taller t ON t.id_taller = ca.id_taller
            GROUP BY i.id_incidente, cp.nombre, ei.nombre
            ORDER BY i.id_incidente DESC
            LIMIT 10
        """)).fetchall()

        if not rows:
            print("  No hay incidentes.")
        else:
            print(f"  {'ID':>4}  {'Categoria':<15}  {'Estado':<12}  {'Cands':^5}  Talleres candidatos")
            print("  " + "-" * 80)
            for r in rows:
                talleres = r.talleres or "--- ninguno"
                print(f"  {r.id_incidente:>4}  {(r.categoria or '---'):<15}  {(r.estado or '---'):<12}  {r.n_candidatos:^5}  {talleres}")

        sep()
        print("  Fin del diagnostico.")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run()
