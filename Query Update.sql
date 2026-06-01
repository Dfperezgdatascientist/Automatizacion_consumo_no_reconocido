SELECT * FROM DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION

-- NOTA: DECIR QUE SOLAMENTE NOS ENVIEN LOS QUE NO TIENEN DECISI”N

select
 A.nvarchar7 , B.decision,A.datetime1,A.datetime2,A.datetime3
FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData A
JOIN Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION B
    ON A.tp_ID = B.tp_ID
where tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
--and A.tp_ID =82005
--AND A.nvarchar7 IS NULL


-- Solo para los que tienen decisiÛn.
UPDATE A
SET A.nvarchar7 = B.decision
 --  ,A.datetime1 = B.FECHA_DECISION_PREVIA,
	--A.datetime2 = B.FECHA_CONTRACARGO,
	--A.datetime3 = B.FECHA_DECISION_DEFINITIVA
FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData A
JOIN Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION B
    ON A.tp_ID = B.tp_ID
where tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
--AND A.nvarchar7 IS NULL



-- ActualizaciÛn Manual

select * from Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION

select count(*) cuenta,Decision from Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION
group by Decision
order by 1 asc

UPDATE Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION
set decision='CONTRACARGADO'
where decision='PARA CONTRACARGO'

DELET E FROM Mantenimiento_UGI.DBO.AUTOSERVICIO_CONSUMOS_NO_RECONOCIDO_DECISION WHERE decision<>'REVERSO CONSUMO D'

UPDATE SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData 
SET nvarchar7 = null
WHERE tp_ID IN (65169,65172,65301,65302,65303,65304,65489,65490,65491,65496,65497,65500,65523,65618,66066,66329,66330,66333,67022,67111,68010,
69180,69741,70215,70235,70309,70350,70351,70674,71682,71683,71855,71856,71857,71884,71885,71886,71888,71890,71891,71892,71893,
71894,71895,71896,71897,71898,71899,71900,71901,71902,71903,71904,71905,71906,71907,71908,71909,71910,71911,72671,72673,72674,
72766,72767,72768,72769,72771,72772,72773,72774,72775,72776,72777,72778,72779,72780,72781,72783,72785,72786,72787,72789,72801,
72802,72803,72804,72806,72958,73081)
and tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x

SELECT tp_ID IdRegistro,nvarchar7 DecisionFinal,nvarchar8,datetime1,datetime2,datetime3,* FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData 
WHERE tp_ID IN (99126,89464)
and tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x

select getdate()

-- ActualizaciÛn de Decisiones

SELECT distinct nvarchar7 FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData 
WHERE 
    tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x

UPDATE SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData 
SET nvarchar7 = 'EXTEMPOR¡NEO GXC'
WHERE nvarchar7 = 'EXTEMPOR√ÅNEO GXC'
and tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x

SELECT distinct nvarchar7 FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData 
where  tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x
order by 1

SELECT * FROM SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData 
WHERE 
    tp_ListId = 'f547c185-e2aa-4bf9-9de6-0c42850b7004'
and tp_DeleteTransactionId = 0x

select * from SharePoint_Content_0225f25502fe4672816c5c7d7d8ebc0c.dbo.AllUserData  where ='3769'

-- Quien fue la persona que modifico
select * from [dbo].[UserInfo]  where  tp_ID like '%3769%'



