-- Proceso para actualizar las decisiones finales en SQL SERVER y TERADATA


-- Tabla creada para importar el archivo 5.188
SELECT * FROM DWH_PRESTAGE.Actualizar_Junio01;

-- Tabla creada para el proceso
select * from DWH_TEMP.Base_Cruce_Decision 

-- Inserci�n de los datos a la tabla final

DELETE FROM DWH_TEMP.Base_Cruce_Decision;

INSERT INTO DWH_TEMP.Base_Cruce_Decision
(
    IdRegistro,
    DecisionFinal,
    FECHA_DECISION_PREVIA,
    FECHA_CONTRACARGO,
    FECHA_DECISION_DEFINITIVA
)
SELECT DISTINCT
    IdRegistro,
    DECISIONFINAL,
    FECHA_DECISION_PREVIA,
    FECHA_CONTRACARGO,
    FECHA_DECISION_DEFINITIVA 
FROM DWH_PRESTAGE.Actualizar_Junio01;


-- Revisar duplicados

select count(distinct IdRegistro) unicos from DWH_TEMP.Base_Cruce_Decision;

-- En el caso de haber duplicados listo..
select count(*) rep, IdRegistro from DWH_TEMP.Base_Cruce_Decision
group by IdRegistro
having count(*)>1;

select count(*) NUMERO, DECISIONFINAL DECISION from DWH_TEMP.Base_Cruce_Decision
group by DECISIONFINAL

DEBITO COMERCIO
DUPLICADO
NO FACTURADO
NO PROCEDE
P&G
PAGA SOCIO
PETICION COPIA DE VALE
CONTRACARGO GANADO
CONTRACARGO PERDIDO
EXCEPCION ALTO VALOR
DEBITO PROVEEDOR
SOCIO RECONOCE CONSUMO
REVISION CONSUMO
ANULADO
RECHAZADO
CONTRACARGADO
DEBITO NEGOCIOS
REINGRESADO
CONSUMO REVERSADO
EXTEMPOR�NEO CLIENTE
EXTEMPOR�NEO GXC

-- Abrir DI en el repositorio DI_PRESTAGE Proyecto: PreStageSharePoint el  JOB: AUTOSERVICIO_CARGA_DECISION00_J y ejecutarlo

-- Atualizaci�n en SQL SERVER

-- Solo para los que no tienen decisi�n.
SELECT * FROM DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION

-- NOTA: DECIR QUE SOLAMENTE NOS ENVIEN LOS QUE NO TIENEN DECISI�N

select
 A.nvarchar7 , B.decision,A.datetime1,A.datetime2,A.datetime3
FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData A
JOIN Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION B
    ON A.tp_ID = B.tp_ID
where tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
--and A.tp_ID =82005
--AND A.nvarchar7 IS NULL


-- Solo para los que tienen decisi�n.
UPDATE A
SET A.nvarchar7 = B.decision
FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData A
JOIN Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION B
    ON A.tp_ID = B.tp_ID
where tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
and B.decision<> NULL

UPDATE A
SET A.datetime1 = B.FECHA_DECISION_PREVIA
FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData A
JOIN Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION B
    ON A.tp_ID = B.tp_ID
where tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
AND B.FECHA_DECISION_PREVIA<>NULL
--AND A.nvarchar7 IS NULL

UPDATE A
SET A.datetime2 = B.FECHA_CONTRACARGO
FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData A
JOIN Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION B
    ON A.tp_ID = B.tp_ID
where tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
AND B.FECHA_CONTRACARGO<>NULL

UPDATE A
SET A.datetime3 = B.FECHA_DECISION_DEFINITIVA
FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData A
JOIN Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION B
    ON A.tp_ID = B.tp_ID
where tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
AND B.FECHA_DECISION_DEFINITIVA<>NULL

--- En Teradata

SELECT A.IdRegistro,A.DecisionFinal,B.DecisionFinal
FROM DWH_DINERS.BASE_CONSUMOS_NO_RECONOCIDOS_FINAL AS A
INNER JOIN  DWH_TEMP.Base_Cruce_Decision B
  ON A.IdRegistro = B.IdRegistro;
  
-- Actualizo las que ya tienen decisi�n final

---Desicionfinal
UPDATE DWH_DINERS.BASE_CONSUMOS_NO_RECONOCIDOS_FINAL AS A
SET DecisionFinal = (
    SELECT B.DecisionFinal
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro
)
WHERE EXISTS (
    SELECT 1
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro 
    AND B.DecisionFinal IS NOT NULL
) AND DecisionFinal IS NULL;

---Fecha_decision_previa
UPDATE DWH_DINERS.BASE_CONSUMOS_NO_RECONOCIDOS_FINAL AS A
SET FECHA_DECISION_PREVIA = (
    SELECT B.FECHA_DECISION_PREVIA
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro
)
WHERE EXISTS (
    SELECT 2
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro 
    AND B.FECHA_DECISION_PREVIA IS NOT NULL
) AND FECHA_DECISION_PREVIA IS NULL;

---Fecha_contracargo
UPDATE DWH_DINERS.BASE_CONSUMOS_NO_RECONOCIDOS_FINAL AS A
SET FECHA_CONTRACARGO = (
    SELECT B.FECHA_CONTRACARGO
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro
)
WHERE EXISTS (
    SELECT 3
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro
    AND B.FECHA_CONTRACARGO IS NOT NULL 
) AND FECHA_CONTRACARGO IS NULL;

---Fecha_decision_definitiva
UPDATE DWH_DINERS.BASE_CONSUMOS_NO_RECONOCIDOS_FINAL AS A
SET FECHA_DECISION_DEFINITIVA = (
    SELECT B.FECHA_DECISION_DEFINITIVA
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro
)
WHERE EXISTS (
    SELECT 1
    FROM DWH_TEMP.Base_Cruce_Decision AS B
    WHERE B.IdRegistro = A.IdRegistro
    AND B.FECHA_DECISION_DEFINITIVA IS NOT NULL  -- solo si B tiene valor
)
AND A.FECHA_DECISION_DEFINITIVA IS NULL;  -- solo si A está vacío



select * from DWH_DINERS.BASE_CONSUMOS_NO_RECONOCIDOS_FINAL where IdRegistro in (99180)

SELECT * FROM DWH_PRESTAGE.Actualizar_Junio01 where IdRegistro in (99126,89464)