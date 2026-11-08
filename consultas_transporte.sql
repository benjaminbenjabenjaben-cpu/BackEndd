-- Consultas externas de Transporte: las mismas 1 a 10 de la página de reportes.
-- Ejecutar en una conexión MySQL local. Este archivo no modifica registros.
USE music_pro_e3;

-- Ejecuta primero estos parámetros. Puedes cambiar los id y las fechas.
SET @tipo_id = (SELECT MIN(id) FROM core_tipovehiculo);
SET @vehiculo_id = (SELECT MIN(id) FROM core_vehiculo);
SET @conductor_id = (SELECT MIN(id) FROM core_conductor);
SET @desde = CURDATE();
SET @hasta = DATE_ADD(CURDATE(), INTERVAL 30 DAY);

-- Django guarda las fechas en UTC. El rango representa días de Santiago.
-- Usa -03:00 o -04:00 según el período consultado.
SET @desfase_local = '-03:00';
SET @desde_utc = CONVERT_TZ(TIMESTAMP(@desde), @desfase_local, '+00:00');
SET @hasta_utc = CONVERT_TZ(TIMESTAMP(DATE_ADD(@hasta, INTERVAL 1 DAY)), @desfase_local, '+00:00');

-- CONSULTA 1: todos los vehículos registrados.
SELECT v.patente, t.nombre AS tipo, v.marca, v.modelo, v.anio, v.disponible
FROM core_vehiculo AS v
JOIN core_tipovehiculo AS t ON t.id = v.tipo_vehiculo_id
ORDER BY v.patente;

-- CONSULTA 2: vehículos de un tipo seleccionado.
SELECT v.patente, t.nombre AS tipo, v.marca, v.modelo, v.anio, v.disponible
FROM core_vehiculo AS v
JOIN core_tipovehiculo AS t ON t.id = v.tipo_vehiculo_id
WHERE v.tipo_vehiculo_id = @tipo_id
ORDER BY v.patente;

-- CONSULTA 3: vehículos disponibles.
SELECT v.patente, t.nombre AS tipo, v.marca, v.modelo, v.anio, v.disponible
FROM core_vehiculo AS v
JOIN core_tipovehiculo AS t ON t.id = v.tipo_vehiculo_id
WHERE v.disponible = TRUE
ORDER BY v.patente;

-- CONSULTA 4: los diez vehículos más antiguos.
SELECT v.patente, t.nombre AS tipo, v.marca, v.modelo, v.anio, v.disponible
FROM core_vehiculo AS v
JOIN core_tipovehiculo AS t ON t.id = v.tipo_vehiculo_id
ORDER BY v.anio, v.id
LIMIT 10;

-- CONSULTA 5: cantidad total de conductores.
SELECT COUNT(*) AS total_conductores
FROM core_conductor;

-- CONSULTA 6: viajes de un vehículo seleccionado.
SELECT j.id AS viaje, v.patente, c.nombre AS conductor, j.origen, j.destino,
       CONVERT_TZ(j.fecha_salida, '+00:00', @desfase_local) AS salida_local,
       j.estado
FROM core_viaje AS j
JOIN core_vehiculo AS v ON v.id = j.vehiculo_id
JOIN core_conductor AS c ON c.id = j.conductor_id
WHERE j.vehiculo_id = @vehiculo_id
ORDER BY j.fecha_salida, j.id;

-- CONSULTA 7: viajes de un conductor seleccionado.
SELECT j.id AS viaje, v.patente, c.nombre AS conductor, j.origen, j.destino,
       CONVERT_TZ(j.fecha_salida, '+00:00', @desfase_local) AS salida_local,
       j.estado
FROM core_viaje AS j
JOIN core_vehiculo AS v ON v.id = j.vehiculo_id
JOIN core_conductor AS c ON c.id = j.conductor_id
WHERE j.conductor_id = @conductor_id
ORDER BY j.fecha_salida, j.id;

-- CONSULTA 8: cantidad de viajes por estado, incluyendo estados sin viajes.
SELECT e.nombre AS estado, COUNT(j.id) AS cantidad
FROM (
    SELECT 1 AS orden, 'programado' AS codigo, 'Programado' AS nombre
    UNION ALL SELECT 2, 'en_curso', 'En curso'
    UNION ALL SELECT 3, 'finalizado', 'Finalizado'
    UNION ALL SELECT 4, 'cancelado', 'Cancelado'
) AS e
LEFT JOIN core_viaje AS j ON j.estado = e.codigo
GROUP BY e.orden, e.codigo, e.nombre
ORDER BY e.orden;

-- CONSULTA 9: viajes programados entre dos fechas locales, ambos días incluidos.
SELECT j.id AS viaje, v.patente, c.nombre AS conductor, j.origen, j.destino,
       CONVERT_TZ(j.fecha_salida, '+00:00', @desfase_local) AS salida_local,
       j.estado
FROM core_viaje AS j
JOIN core_vehiculo AS v ON v.id = j.vehiculo_id
JOIN core_conductor AS c ON c.id = j.conductor_id
WHERE j.estado = 'programado'
  AND j.fecha_salida >= @desde_utc
  AND j.fecha_salida < @hasta_utc
ORDER BY j.fecha_salida, j.id;

-- CONSULTA 10: vehículos que no tienen viajes registrados.
SELECT v.patente, t.nombre AS tipo, v.marca, v.modelo, v.anio, v.disponible
FROM core_vehiculo AS v
JOIN core_tipovehiculo AS t ON t.id = v.tipo_vehiculo_id
LEFT JOIN core_viaje AS j ON j.vehiculo_id = v.id
WHERE j.id IS NULL
ORDER BY v.patente;
