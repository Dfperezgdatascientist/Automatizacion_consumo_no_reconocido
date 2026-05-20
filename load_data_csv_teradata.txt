#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Carga parquet a Teradata — Optimizado con FastLoad para volúmenes de 18M+ registros.
 
Mejoras sobre versión anterior:
  - batch_size: 1.500 → 100.000 filas por lote
  - df.rows() reemplazado por iteración por chunks en Polars (no carga todo en RAM de una)
  - Protocolo FastLoad de Teradata activado via parámetro de sesión
  - Limpieza de caracteres no-LATIN antes de insertar (evita error 6706)
  - commit cada lote (no acumular transacciones enormes)
  - Métricas de velocidad por lote (filas/segundo)
"""
 
import sys
import logging
import unicodedata
import time
from datetime import datetime
from pathlib import Path
 
import polars as pl
import teradatasql
from teradatasql import OperationalError
import urllib3
 
# Deshabilitar warning de InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
 
# ===== Teradata =====
TD_HOSTS = ["10.100.232.23", "10.100.232.24"]
TD_USER  = "DwhCarga"
TD_PASS  = "DN.2020#05"
 
TD_CONN_BASE = {
    "user":        TD_USER,
    "password":    TD_PASS,
    "logmech":     "TD2",
    "encryptdata": "true",
}
 
FINAL_TABLE = "dwh_temp.tmp_ISD_2025_UGI_2"
 
# ===== Parámetros de carga — ajusta según RAM disponible =====
BATCH_SIZE  = 100_000   # filas por lote en executemany  (era 1.500)
CHUNK_SIZE  = 500_000   # filas por chunk leído de Polars (no carga 18M de golpe en RAM)
 
 
# ============================================================
# Conexión Teradata con fallback de hosts
# ============================================================
def _connect_teradata():
    last = None
    for host in TD_HOSTS:
        try:
            cfg = dict(TD_CONN_BASE)
            cfg["host"] = host
            logging.info("Conectando a Teradata %s ...", host)
            return teradatasql.connect(**cfg)
        except Exception as e:
            last = e
            logging.warning("Fallo conectando a %s: %s", host, e)
    raise last
 
 
# ============================================================
# Logging
# ============================================================
def setup_logging(yyyy, mm, dd, hh):
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    log_filename = logs_dir / f"carga_isd_UGI_{yyyy}{mm}{dd}_{hh}.log"
 
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
 
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
 
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
 
    fh = logging.FileHandler(log_filename, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
 
    logger.addHandler(ch)
    logger.addHandler(fh)
    return log_filename
 
 
# ============================================================
# Utilidades de nombre de columna
# ============================================================
def sanitize_col(col: str) -> str:
    """Elimina tildes y caracteres especiales del nombre de columna."""
    normalized = "".join(
        c for c in unicodedata.normalize("NFD", col)
        if unicodedata.category(c) != "Mn"
    )
    return (
        normalized
        .replace(" ", "_").replace("-", "_")
        .replace("(", "").replace(")", "")
        .replace(".", "_").strip()
    )
 
 
# ============================================================
# DDL dinámico
# ============================================================
def get_teradata_type(dtype) -> str:
    if dtype == pl.Float64 or dtype == pl.Float32:
        return "DECIMAL(18,4)"
    elif dtype in (pl.Int64, pl.Int32, pl.Int16, pl.Int8, pl.UInt32, pl.UInt64):
        return "BIGINT"
    elif dtype == pl.Boolean:
        return "BYTEINT"
    elif dtype == pl.Date:
        return "DATE FORMAT 'YYYY-MM-DD'"
    elif dtype == pl.Datetime:
        return "TIMESTAMP(0)"
    else:
        return "VARCHAR(4096) CHARACTER SET UNICODE"
 
 
def drop_table_if_exists(con, cur, table_name: str):
    try:
        db, tbl = table_name.split(".", 1)
        cur.execute(
            f"SELECT 1 FROM DBC.TablesV "
            f"WHERE DatabaseName='{db.upper()}' AND TableName='{tbl.upper()}' AND TableKind='T'"
        )
        if cur.fetchone() is not None:
            logging.info("Tabla %s existe. Eliminando...", table_name)
            cur.execute(f"DROP TABLE {table_name}")
            con.commit()
            logging.info("Tabla %s eliminada.", table_name)
    except Exception as e:
        logging.warning("No se pudo verificar/eliminar tabla: %s", e)
 
 
def create_table_from_schema(con, cur, table_name: str, schema: dict):
    col_defs = []
    first_col = None
    for col, dtype in schema.items():
        td_type = get_teradata_type(dtype)
        col_defs.append(f"  {col} {td_type}")
        if first_col is None:
            first_col = col
 
    create_sql = (
        f"CREATE MULTISET TABLE {table_name} (\n"
        + ",\n".join(col_defs)
        + f"\n) PRIMARY INDEX ({first_col});"
    )
    logging.info("DDL (primeros 400 chars): %s", create_sql[:400])
    cur.execute(create_sql)
    con.commit()
    logging.info("Tabla %s creada.", table_name)
 
 
# ============================================================
# Limpieza de valores no-LATIN (evita error 6706)
# ============================================================
_LATIN_SAFE = set(range(32, 127)) | set(range(160, 256))
 
def _clean_value(v):
    """Elimina caracteres fuera de ISO-8859-1 en strings."""
    if not isinstance(v, str):
        return v
    return "".join(ch if ord(ch) in _LATIN_SAFE else " " for ch in v).strip()
 
def _clean_row(row: tuple) -> tuple:
    return tuple(_clean_value(v) for v in row)
 
 
# ============================================================
# Inserción optimizada por chunks + FastLoad
# ============================================================
def insert_chunks(cur, con, insert_sql: str, df: pl.DataFrame, total_rows: int):
    """
    Itera el DataFrame en chunks de CHUNK_SIZE y dentro de cada chunk
    hace lotes de BATCH_SIZE con executemany.
    """
    total_inserted = 0
    chunk_start = 0
 
    while chunk_start < total_rows:
        chunk_end = min(chunk_start + CHUNK_SIZE, total_rows)
        chunk_df  = df.slice(chunk_start, chunk_end - chunk_start)
 
        # Polars → lista de tuplas (solo el chunk en RAM)
        rows = chunk_df.rows()
 
        chunk_inserted = 0
        t_chunk = time.time()
 
        for i in range(0, len(rows), BATCH_SIZE):
            batch = [_clean_row(r) for r in rows[i : i + BATCH_SIZE]]
            try:
                cur.executemany(insert_sql, batch)
                con.commit()
                chunk_inserted += len(batch)
                total_inserted += len(batch)
 
            except OperationalError as e:
                logging.warning("Error en lote — reintentando fila a fila: %s", e)
                con.rollback()
                ok = 0
                for row in batch:
                    try:
                        cur.execute(insert_sql, row)
                        ok += 1
                    except OperationalError as e2:
                        logging.error("Fila descartada: %s | Error: %s", row, e2)
                con.commit()
                chunk_inserted += ok
                total_inserted += ok
 
        elapsed   = time.time() - t_chunk
        rps       = chunk_inserted / elapsed if elapsed > 0 else 0
        pct       = total_inserted / total_rows * 100
        logging.info(
            "Chunk %d-%d | insertadas: %d | acumulado: %d / %d (%.1f%%) | %.0f filas/seg",
            chunk_start, chunk_end, chunk_inserted, total_inserted, total_rows, pct, rps
        )
 
        chunk_start = chunk_end
 
    return total_inserted
 
 
# ============================================================
# Main
# ============================================================
def main():
    start_time = time.time()
 
    now  = datetime.now()
    yyyy = now.strftime("%Y")
    mm   = now.strftime("%m")
    dd   = now.strftime("%d")
    hh   = now.strftime("%H")
 
    log_file = setup_logging(yyyy, mm, dd, hh)
    logging.info("=" * 80)
    logging.info("Iniciando carga parquet ISD 2025 UGI  —  FastLoad optimizado")
    logging.info("BATCH_SIZE=%d | CHUNK_SIZE=%d", BATCH_SIZE, CHUNK_SIZE)
    logging.info("Log: %s", log_file)
    logging.info("=" * 80)
 
    # ── Leer parquet ──────────────────────────────────────────
    parquet_path = Path(r"./base/ISD_2025_UGI.parquet")
    if not parquet_path.exists():
        logging.error("Parquet no encontrado: %s", parquet_path)
        sys.exit(1)
 
    logging.info("Cargando parquet: %s", parquet_path)
    df = pl.read_parquet(parquet_path)
    logging.info("Parquet cargado. Filas: %d | Columnas: %d", df.height, df.width)
 
    # ── Sanitizar nombres de columna ──────────────────────────
    rename_dict = {col: sanitize_col(col) for col in df.columns}
    df = df.rename(rename_dict)
    logging.info("Columnas sanitizadas: %s", df.columns)
 
    # ── Conexión y carga ──────────────