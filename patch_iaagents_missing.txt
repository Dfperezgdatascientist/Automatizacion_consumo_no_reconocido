#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import subprocess
import logging
from datetime import datetime
import pandas as pd
import teradatasql

# variables de conexion teradata
TD_HOSTS = ["10.100.232.23", "10.100.232.24"]
TD_USER = "DwhCarga"
TD_PASS = "DN.2020#05"

# ===== Tabla de alertas para patches =====
PATCH_ALERT_TABLE = "DWH_PRESTAGE.V_ALERTAS_IAAGENTS"

CREATE_PATCH_ALERT_TABLE_SQL = f"""
CREATE TABLE {PATCH_ALERT_TABLE} (
  fecha_carga DATE,
  hora_carga VARCHAR(2),
  tipo_alerta VARCHAR(20),
  status VARCHAR(20),
  registro_timestamp TIMESTAMP(6)
)
PRIMARY INDEX (fecha_carga, hora_carga)
"""

CHECK_PATCH_ALERT_EXISTS_SQL = f"""
SEL 1
FROM DBC.TablesV
WHERE DatabaseName='DWH_PRESTAGE'
  AND TableName='V_ALERTAS_IAAGENTS'
  AND TableKind='T'
"""

CHECK_FINAL_EXISTS_SQL = """
SEL 1
FROM DBC.TablesV
WHERE DatabaseName='DWH_PRESTAGE'
  AND TableName='IAAGENTS_S3'
  AND TableKind='T'
"""

def ensure_patch_alert_exists(conn, cur):
    cur.execute(CHECK_PATCH_ALERT_EXISTS_SQL)
    if cur.fetchone() is None:
        logger.info("Creando tabla de alertas de patch %s ...", PATCH_ALERT_TABLE)
        try:
            cur.execute(CREATE_PATCH_ALERT_TABLE_SQL)
            conn.commit()
            logger.info("Tabla de alertas de patch creada.")
        except Exception as e:
            logger.warning("No se pudo crear la tabla de alertas de patch. Asegúrate de que exista o tenga permisos: %s", e)
            # No salir, asumir que existe o continuar sin ella

def connect_teradata():
    for host in TD_HOSTS:
        try:
            logger.debug(f"Intentando conectar a Teradata en host: {host}")
            conn = teradatasql.connect(
                host=host,
                user=TD_USER,
                password=TD_PASS,
                logmech="TD2",
                encryptdata="true"
            )
            logger.info(f"Conexión exitosa a Teradata en host: {host}")
            return conn
        except Exception as e:
            logger.warning(f"Fallo conectando a {host}: {e}")
    logger.error("No se pudo conectar a ningún host de Teradata después de intentar todos")
    raise Exception("No se pudo conectar a ningún host")

PATCH_SCRIPT = "load_iaagents_json_to_teradata.py"

# Configurar logging tanto a consola como a archivo
log_filename = f"logs/patch_iaagents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Handler para archivo
file_handler = logging.FileHandler(log_filename, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(file_formatter)

# Handler para consola
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
console_handler.setFormatter(console_formatter)

logger.addHandler(file_handler)
logger.addHandler(console_handler)


def get_missing_slots():
    logger.info("Consultando horas faltantes...")
    
    query = """SELECT fecha_generada, hora_generada
FROM (
    SELECT CURRENT_DATE - 1 AS fecha_generada,
           -- LPAD garantiza '00', '01', '02' ... '23'
           LPAD(TRIM(CAST(hora_seq AS VARCHAR(2))), 2, '0') AS hora_generada
    FROM (
        SELECT  0 AS hora_seq FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  1             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  2             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  3             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  4             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  5             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  6             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  7             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  8             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT  9             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 10             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 11             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 12             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 13             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 14             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 15             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 16             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 17             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 18             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 19             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 20             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 21             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 22             FROM (SEL 1 AS x) AS t UNION ALL
        SELECT 23             FROM (SEL 1 AS x) AS t
    ) AS horas_ref
) AS todas_combinaciones
LEFT JOIN DWH_PRESTAGE.IAAGENTS_S3 AS registros
    ON  todas_combinaciones.fecha_generada = registros.fecha_carga
    AND todas_combinaciones.hora_generada  = registros.hora_carga
WHERE registros.fecha_carga IS NULL
ORDER BY fecha_generada, hora_generada;"""

    try:
        with connect_teradata() as conn:
            cursor = conn.cursor()
            cursor.execute(query)

            rows = cursor.fetchall()
            cols = [col[0] for col in cursor.description]

        df = pd.DataFrame(rows, columns=cols)
        ## prueba
        # df.loc[len(df)] = ["2026-03-16", "10"]
        # df.loc[len(df)] = ["2026-03-16", "11"]
        logger.info(f"Query ejecutada exitosamente. Registros encontrados: {len(df)}")
        if df.empty:
            logger.info("No hay horas faltantes en la tabla IAAGENTS_S3")
        else:
            logger.info(f"Horas faltantes:\n{df.to_string()}")
        return df
    except Exception as e:
        logger.error(f"Error al consultar horas faltantes: {e}", exc_info=True)
        raise


def run_patch(fecha, hora):
    fecha_fmt = datetime.strptime(str(fecha), "%Y-%m-%d").strftime("%Y%m%d")
    hora_fmt = str(hora).zfill(2)

    cmd = [
        sys.executable,
        PATCH_SCRIPT,
        fecha_fmt,
        hora_fmt
    ]

    logger.info(f"Ejecutando patch: {' '.join(cmd)}")
    logger.debug(f"Comando completo: {cmd}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        status = "EXITO" if result.returncode == 0 else "ERROR"

        # Insertar alerta en Teradata
        try:
            with connect_teradata() as conn:
                cur = conn.cursor()
                ensure_patch_alert_exists(conn, cur)
                cur.execute(
                    f"INSERT INTO {PATCH_ALERT_TABLE} (fecha_carga, hora_carga, tipo_alerta, status, registro_timestamp) VALUES (?, ?, 'PATCH', ?, CURRENT_TIMESTAMP)",
                    (fecha, hora_fmt, status)
                )
                conn.commit()
                logger.info(f"Alerta de patch registrada en {PATCH_ALERT_TABLE}")
        except Exception as e:
            logger.warning(f"No se pudo insertar alerta de patch: {e}. Continuando.")

        if result.returncode == 0:
            logger.info(f"Patch ejecutado exitosamente para fecha={fecha_fmt}, hora={hora_fmt}")
            if result.stdout:
                logger.debug(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"Patch falló para fecha={fecha_fmt}, hora={hora_fmt} con código: {result.returncode}")
            if result.stdout:
                logger.error(f"StdOut: {result.stdout}")
            if result.stderr:
                logger.error(f"StdErr: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Excepción al ejecutar patch para fecha={fecha_fmt}, hora={hora_fmt}: {e}", exc_info=True)
        # Insertar alerta de error
        try:
            with connect_teradata() as conn:
                cur = conn.cursor()
                ensure_patch_alert_exists(conn, cur)
                cur.execute(
                    f"INSERT INTO {PATCH_ALERT_TABLE} (fecha_carga, hora_carga, tipo_alerta, status, registro_timestamp) VALUES (?, ?, 'PATCH', 'ERROR', CURRENT_TIMESTAMP)",
                    (fecha, hora_fmt)
                )
                conn.commit()
                logger.info(f"Alerta de error de patch registrada en {PATCH_ALERT_TABLE}")
        except Exception as e2:
            logger.warning(f"No se pudo insertar alerta de error: {e2}. Continuando.")
        return False


def delete_duplicates():
    logger.info("Iniciando eliminación de duplicados en Teradata...")

    query = """
    DELETE FROM DWH_PRESTAGE.IAAGENTS_S3
    WHERE session_uuid IN (
        select session_uuid from (
            select session_uuid,message_message_id,count(*) cuenta,
                   min(etlTstamp) etlTstamp
            from DWH_PRESTAGE.IAAGENTS_S3
            group by session_uuid,message_message_id
            having count(*)>1
        ) a
    )
    AND etlTstamp IN (
        select etlTstamp from (
            select session_uuid,message_message_id,count(*) cuenta,
                   min(etlTstamp) etlTstamp
            from DWH_PRESTAGE.IAAGENTS_S3
            group by session_uuid,message_message_id
            having count(*)>1
        ) a
    )
    """

    try:
        with connect_teradata() as conn:
            cursor = conn.cursor()
            logger.debug("Ejecutando query de eliminación de duplicados...")
            cursor.execute(query)
            rows_deleted = cursor.rowcount
            conn.commit()
            logger.info(f"Duplicados eliminados exitosamente. Registros eliminados: {rows_deleted}")
    except Exception as e:
        logger.error(f"Error al eliminar duplicados: {e}", exc_info=True)
        raise


def main():
    logger.info("=" * 80)
    logger.info("INICIANDO PROCESO PATCH IAAGENTS")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 80)

    # Asegurar que la tabla de alertas de patch exista
    try:
        with connect_teradata() as conn:
            cur = conn.cursor()
            ensure_patch_alert_exists(conn, cur)
    except Exception as e:
        logger.warning(f"No se pudo verificar/crear tabla de alertas de patch: {e}. Continuando sin ella.")

    # Validar que la tabla final exista
    try:
        with connect_teradata() as conn:
            cur = conn.cursor()
            cur.execute(CHECK_FINAL_EXISTS_SQL)
            if cur.fetchone() is None:
                logger.error("La tabla final DWH_PRESTAGE.IAAGENTS_S3 no existe. No se puede ejecutar el patch.")
                sys.exit(1)
    except Exception as e:
        logger.error(f"Error al validar existencia de tabla final: {e}")
        sys.exit(1)

    try:
        df = get_missing_slots()

        logger.info(f"Total de horas sin información: {df.shape[0]}")

        errores = 0
        exitosos = 0

        if df.empty:
            logger.info("? No hay horas faltantes. Proceso sin cambios requeridos.")
        else:
            procesados = set()

            for index, row in df.iterrows():
                fecha = row["fecha_generada"]
                hora = row["hora_generada"]

                key = f"{fecha}_{hora}"

                if key in procesados:
                    logger.debug(f"Saltando {key} - Ya procesado")
                    continue

                logger.info(f"Procesando [{index + 1}/{len(df)}] fecha={fecha}, hora={hora}")

                ok = run_patch(fecha, hora)

                if ok:
                    procesados.add(key)
                    exitosos += 1
                    logger.info(f"? Patch exitoso para {key}")
                else:
                    errores += 1
                    logger.error(f"? Patch FALLÓ para {key}")

            logger.info(f"Resumen: {exitosos} exitosos, {errores} errores")

            # limpieza duplicados
            if exitosos > 0:
                logger.info("Iniciando limpieza de duplicados...")
                delete_duplicates()
                logger.info("? Limpieza de duplicados completada")
            else:
                logger.warning("No se ejecutaron patches exitosos, saltando limpieza de duplicados")

        logger.info("=" * 80)
        if errores > 0:
            logger.error(f"? PROCESO FINALIZADO CON ERRORES ({errores} fallos)")
            logger.info("=" * 80)
            sys.exit(1)

        logger.info("? PROCESO FINALIZADO EXITOSAMENTE")
        logger.info(f"Archivo de log: {log_filename}")
        logger.info("=" * 80)
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"? Error crítico en el proceso principal: {e}", exc_info=True)
        logger.error("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()