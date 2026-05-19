import os
import pyodbc
import teradatasql
import pandas as pd
try:
    import polars as pl
except ImportError:
    pl = None
import numpy as np
import logging
import time
try:
    import mysql.connector
except ImportError:
    mysql = None
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

HAS_POLARS = pl is not None

# Configuración de logging
log_filename = f'log/Stock_Salas_Vip_QR_{datetime.now().strftime("%Y-%m-%d")}.log'
logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# ================= CONFIGURACIÓN =================

MYSQL_HOST = "98.94.237.150"
MYSQL_PORT = 3306
MYSQL_DB = "blu_metadata" #"blu_metadata_preprod"
MYSQL_UID = "beneficio_personalizado_prod" #"beneficio_personalizado_pre"
MYSQL_PWD = "SXcEiiG9scrtxfbh" #"ofHEkiqQK7LKDFrJ"
MYSQL_TABLE = "tabSalasVIP"

# # ================= CONFIGURACIÓN =================
# MYSQL_HOST = "98.94.237.150"
# MYSQL_PORT = 3306
# MYSQL_DB = "blu_metadata_preprod"
# MYSQL_UID = "beneficio_personalizado_pre"
# MYSQL_PWD = "ofHEkiqQK7LKDFrJ"
# MYSQL_TABLE = "tabSalasVIP"

TD_HOSTS = ["10.100.232.23", "10.100.232.24"]
TD_USER = "dwhcarga"
TD_PASS = "DN.2020#05"


BATCH_SIZE = int(os.getenv("BATCH_SIZE", "500"))  # con DF suele ir mejor 1000-5000


# ================= CONEXIONES =================
def conectar_mysql():
    """
    Intenta conectar a MySQL usando ODBC, si no está disponible usa mysql.connector
    """
    # Intentar con ODBC primero
    drivers = [d for d in pyodbc.drivers() if "MySQL ODBC" in d]
    if drivers:
        driver = drivers[-1]
        logging.info(f"Usando driver MySQL ODBC: {driver}")
        return pyodbc.connect(
            f"DRIVER={{{driver}}};"
            f"SERVER={MYSQL_HOST};"
            f"PORT={MYSQL_PORT};"
            f"DATABASE={MYSQL_DB};"
            f"UID={MYSQL_UID};"
            f"PWD={MYSQL_PWD};"
            "CHARSET=utf8mb4;"
        )
    
    # Fallback a mysql.connector si está disponible
    if mysql is not None:
        logging.info("Driver MySQL ODBC no encontrado. Usando mysql.connector...")
        try:
            return mysql.connector.connect(
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_UID,
                password=MYSQL_PWD,
                database=MYSQL_DB,
                charset='utf8mb4'
            )
        except Exception as e:
            logging.error(f"Error conectando con mysql.connector: {e}")
            raise RuntimeError(f"No se pudo conectar a MySQL: {e}")
    
    raise RuntimeError("No se encontró driver 'MySQL ODBC' instalado. Instala: pip install mysql-connector-python")


def conectar_teradata():
    last_err = None
    for host in TD_HOSTS:
        try:
            return teradatasql.connect(
                host=host,
                user=TD_USER,
                password=TD_PASS,
                logmech="TD2"
            )
        except Exception as e:
            last_err = e
    raise RuntimeError(f"No se pudo conectar a Teradata: {last_err}")


# show table

def mostrar_ddl_tabla_mysql():
    """
    Ejecuta SHOW CREATE TABLE tabSalasVIP
    y muestra el DDL real desde MySQL.
    """
    with conectar_mysql() as my:
        cur = my.cursor()
        cur.execute("SHOW CREATE TABLE tabSalasVIP")
        row = cur.fetchone()

        print("\n===== SHOW CREATE TABLE tabSalasVIP =====\n")
        # row[0] = nombre de la tabla
        # row[1] = DDL completo
        print(row[1])
        print("\n========================================\n")


# select

def mostrar_select_top_100_mysql():
    """
    Ejecuta un SELECT LIMIT 100 sobre tabSalasVIP
    y muestra los resultados en consola.
    """
    with conectar_mysql() as my:
        cur = my.cursor()

        sql = """
        SELECT
            name,
            identificacion,
            numero_accesos_socio_principal,
            mes_validez,
            politica_adicional,
            tarifa_acceso_principal_subtotal,
            tarifa_acceso_principal_iva,
            tarifa_acceso_principal_total,
            numero_acompanantes_gratuitos,
            tarifa_acceso_acompanantes_subtotal,
            tarifa_acceso_acompanantes_iva,
            tarifa_acceso_acompanantes_total,
            tiene_redireccion_concierge,
            url_concierge,
            tiene_acceso_lounge,
            fecha_actualizacion
        FROM tabSalasVIP
        LIMIT 100
        """

        cur.execute(sql)
        rows = cur.fetchall()

        print("\n===== SELECT TOP 100 (MySQL LIMIT 100) =====\n")

        for i, row in enumerate(rows):
            print(f"Fila {i}:")
            for idx, col in enumerate(row):
                print(f"  Col {idx}: {col} (type={type(col).__name__})")
            print("-" * 40)

        print(f"\n✅ Total filas mostradas: {len(rows)}")
        print("\n===========================================\n")


# select count()

def mostrar_dataframe(df, rows=5):
    """
    Muestra las primeras filas de un DataFrame (compatible con Pandas y Polars)
    """
    if HAS_POLARS and isinstance(df, pl.DataFrame):
        print(df.head(rows))
    else:
        print(df.head(rows).to_string(index=False))


def mostrar_count_mysql():
    """
    Ejecuta SELECT COUNT(*) sobre tabSalasVIP
    y muestra el total de registros en consola.
    """
    with conectar_mysql() as my:
        cur = my.cursor()

        sql = "SELECT COUNT(*) FROM tabSalasVIP"
        cur.execute(sql)

        total = cur.fetchone()[0]

        print("\n===== COUNT(*) tabSalasVIP =====")
        print(f"✅ Total registros: {total}")
        print("================================\n")




# ================= ETL =================
def cargar_teradata_a_dataframe():
    """
    Lee la tabla de Teradata y la carga en memoria.
    Si Polars está disponible, usa Polars para las transformaciones en memoria.
    """
    td_sql = """
    SELECT
        TRIM(name) AS name,
        TRIM(identificacion) AS identificacion,
        numero_accesos_socio_principal,
        mes_validez,
        politica_adicional,
        tarifa_acceso_principal_subtotal,
        tarifa_acceso_principal_iva,
        tarifa_acceso_principal_total,
        numero_acompanantes_gratuitos,
        tarifa_acceso_acompanantes_subtotal,
        tarifa_acceso_acompanantes_iva,
        tarifa_acceso_acompanantes_total,
        tiene_redireccion_concierge,
        url_concierge,
        tiene_acceso_lounge,
        fecha_actualizacion
    FROM DWH_DINERS.STOCK_SOCIOS_SALAS_VIP_QR_DIGITAL
    """

    cols = [
        "name",
        "identificacion",
        "numero_accesos_socio_principal",
        "mes_validez",
        "politica_adicional",
        "tarifa_acceso_principal_subtotal",
        "tarifa_acceso_principal_iva",
        "tarifa_acceso_principal_total",
        "numero_acompanantes_gratuitos",
        "tarifa_acceso_acompanantes_subtotal",
        "tarifa_acceso_acompanantes_iva",
        "tarifa_acceso_acompanantes_total",
        "tiene_redireccion_concierge",
        "url_concierge",
        "tiene_acceso_lounge",
        "fecha_actualizacion"
    ]

    with conectar_teradata() as td:
        df = pd.read_sql_query(td_sql, td)

    if HAS_POLARS:
        df = pl.from_pandas(df)
        df = df.with_columns([
            pl.col("name").str.strip_chars(),
            pl.col("identificacion").str.strip_chars()
        ]).select(cols)
        return df

    df = df[cols]
    df["name"] = df["name"].astype(str).str.strip()
    df["identificacion"] = df["identificacion"].astype(str).str.strip()

    return df

# para entrar borrando la tabla de mysql
def truncate_mysql():
    with conectar_mysql() as my:
        cur = my.cursor()
        try:
            cur.execute(f"DELETE FROM {MYSQL_TABLE}")
            my.commit()
            affected_rows = cur.rowcount
            print(f"🧹 DELETE ejecutado: {MYSQL_TABLE} ({affected_rows} filas eliminadas)")
            logging.info(f"Tabla {MYSQL_TABLE} limpiada. Filas eliminadas: {affected_rows}")
        except Exception as e:
            logging.error(f"Error al limpiar tabla {MYSQL_TABLE}: {e}")
            raise

# anterior version de insert (mas lento)
#def insertar_dataframe_a_mysql(df: pd.DataFrame):
#    mysql_insert = f"""
#    INSERT INTO {MYSQL_TABLE} (
#        name,
#        identificacion,
#        numero_accesos_socio_principal,
#        mes_validez,
#        politica_adicional,
#        tarifa_acceso_principal_subtotal,
#        tarifa_acceso_principal_iva,
#        tarifa_acceso_principal_total,
#        numero_acompanantes_gratuitos,
#        tarifa_acceso_acompanantes_subtotal,
#        tarifa_acceso_acompanantes_iva,
#        tarifa_acceso_acompanantes_total,
#        tiene_redireccion_concierge,
#        url_concierge,
#        tiene_acceso_lounge,
#        fecha_actualizacion
#    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
#    """
#
#    with conectar_mysql() as my:
#        cur = my.cursor()
#        cur.fast_executemany = True #False #True
#
#        total = len(df)
#        print(f"📦 Filas a insertar: {total}")
#
#        # Convertir DF a lista de tuplas (None para NaN)
#        records = df.where(pd.notnull(df), None).itertuples(index=False, name=None)
#
#        batch = []
#        inserted = 0
#
#        for row in records:
#            batch.append(row)
#            if len(batch) >= BATCH_SIZE:
#                cur.executemany(mysql_insert, batch)
#                my.commit()
#                inserted += cur.rowcount
#                print(f"✅ Batch insertado: {cur.rowcount} | Acumulado: {inserted}")
#                batch = []
#
#        if batch:
#            cur.executemany(mysql_insert, batch)
#            my.commit()
#            inserted += cur.rowcount
#            print(f"✅ Batch final insertado: {cur.rowcount} | Total: {inserted}")



# Insert a mysql
def insertar_mysql_ultra_rapido(df, batch_size=BATCH_SIZE, ignore_duplicates=True):
    """
    Inserta datos en MySQL rápidamente usando batches.
    
    Args:
        df: DataFrame (Pandas o Polars)
        batch_size: Tamaño del lote de inserción
        ignore_duplicates: Si es True, usa INSERT IGNORE para evitar errores de duplicados
    """
    cols = [
        "name","identificacion","numero_accesos_socio_principal","mes_validez","politica_adicional",
        "tarifa_acceso_principal_subtotal","tarifa_acceso_principal_iva","tarifa_acceso_principal_total",
        "numero_acompanantes_gratuitos",
        "tarifa_acceso_acompanantes_subtotal","tarifa_acceso_acompanantes_iva","tarifa_acceso_acompanantes_total",
        "tiene_redireccion_concierge","url_concierge","tiene_acceso_lounge","fecha_actualizacion"
    ]

    if HAS_POLARS and isinstance(df, pl.DataFrame):
        df = df.to_pandas()

    if "name" not in df.columns:
        df["identificacion"] = df["identificacion"].astype(str).str.strip()
        df["name"] = df["identificacion"]

    with conectar_mysql() as my:
        cur = my.cursor()
        
        # Detectar si es mysql.connector o pyodbc
        is_mysql_connector = mysql is not None and hasattr(cur, 'execute') and 'mysql' in str(type(cur))
        
        if is_mysql_connector:
            param_char = "%s"
        else:
            param_char = "?"
            cur.fast_executemany = False  # 👈 CLAVE con pyodbc

        # Usar INSERT IGNORE si se especifica
        insert_keyword = "INSERT IGNORE INTO" if ignore_duplicates else "INSERT INTO"
        insert_prefix = f"{insert_keyword} {MYSQL_TABLE} ({','.join(cols)}) VALUES "
        row_tpl = "(" + ",".join([param_char] * len(cols)) + ")"

        # optimizaciones seguras
        try:
            cur.execute("SET autocommit=0")
            cur.execute("SET unique_checks=0")
            cur.execute("SET foreign_key_checks=0")
        except Exception as e:
            logging.warning(f"No se pudieron establecer opciones de autocommit: {e}")

        total = 0
        duplicados = 0
        batch = []

        for row in df[cols].itertuples(index=False, name=None):
            batch.append(row)
            if len(batch) >= batch_size:
                sql = insert_prefix + ",".join([row_tpl] * len(batch))
                params = [v for r in batch for v in r]
                try:
                    cur.execute(sql, params)
                    my.commit()
                    total += cur.rowcount
                    print(f"✅ Insertadas: {total}")
                except Exception as e:
                    logging.error(f"Error insertando batch: {e}")
                    if ignore_duplicates:
                        duplicados += 1
                    else:
                        raise
                batch = []

        if batch:
            sql = insert_prefix + ",".join([row_tpl] * len(batch))
            params = [v for r in batch for v in r]
            try:
                cur.execute(sql, params)
                my.commit()
                total += cur.rowcount
                print(f"✅ Total final: {total}")
            except Exception as e:
                logging.error(f"Error insertando batch final: {e}")
                if ignore_duplicates:
                    duplicados += 1
                else:
                    raise

        try:
            cur.execute("SET foreign_key_checks=1")
            cur.execute("SET unique_checks=1")
            cur.execute("SET autocommit=1")
        except Exception as e:
            logging.warning(f"No se pudieron restaurar opciones de autocommit: {e}")
        
        if duplicados > 0:
            logging.info(f"Registros duplicados ignorados: {duplicados}")
            print(f"⚠️ Registros duplicados ignorados: {duplicados}")


def mostrar_count_mysql():
    with conectar_mysql() as my:
        cur = my.cursor()
        cur.execute(f"SELECT COUNT(*) FROM {MYSQL_TABLE}")
        total = cur.fetchone()[0]
        print(f"🔢 COUNT(*) {MYSQL_TABLE}: {total}")


# ================= MAIN =================
if __name__ == "__main__":
    start_time = time.time()
    logging.info("Inicio del proceso de carga de Stock Salas VIP QR")

    mostrar_count_mysql()        # Conteo antes
    #mostrar_ddl_tabla_mysql()   # <-- VALIDACIÓN DD


    df = cargar_teradata_a_dataframe()
    print("🧾 DataFrame cargado desde Teradata:", df.shape)
    mostrar_dataframe(df, rows=5)


    # vaciar tabla antes de cargar
    truncate_mysql()

    # insertar datos a la tabla
    #insertar_dataframe_a_mysql(df) # <-- metodo anterior (mas lento)
    insertar_mysql_ultra_rapido(df,batch_size=1500)
    

    mostrar_select_top_100_mysql()   # <-- Ver datos cargados
    mostrar_count_mysql()        # Conteo después

    end_time = time.time()
    total_time = end_time - start_time
    logging.info(f"Proceso completado. Tiempo total de procesamiento: {total_time:.2f} segundos")
    print(f"⏱️ Tiempo total de procesamiento: {total_time:.2f} segundos")