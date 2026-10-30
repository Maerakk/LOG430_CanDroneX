-- 300 000 drones de mesure (un drone neuf par commande du test de charge)
SET SESSION cte_max_recursion_depth = 400000;
INSERT INTO drone (client_id, drone_id, imsi, iccid, status)
WITH RECURSIVE seq (n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM seq WHERE n < 300000)
SELECT 'inspectra-demo', CONCAT('LOAD-', n), CONCAT('30299', LPAD(n, 10, '0')), CONCAT('893029900', LPAD(n, 10, '0')), 'active'
FROM seq;
