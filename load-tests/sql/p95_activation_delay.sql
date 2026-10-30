-- P95 du délai entre accepted_at et activated_at. @ordered est le nombre d'éléments commandés, lu dans la base des commandes.
-- Un service non actif à la fin est classé après les autres : il compte comme > 5 s.
SET @ordered = COALESCE(@ordered, (SELECT COUNT(*) FROM service WHERE accepted_at BETWEEN @start AND @end));
SET @p95_rank = CEIL(0.95 * @ordered);

SELECT @ordered                                        AS ordered_items,
       COUNT(*)                                        AS received_items,
       SUM(state = 'ACTIVE')                           AS active_items,
       SUM(state IN ('PENDING', 'ACTIVATING', 'UNKNOWN')) AS not_finished_items,
       SUM(state = 'FAILED')                           AS failed_items,
       @p95_rank                                       AS p95_rank,
       COALESCE((
           SELECT delay_ms FROM (
               SELECT TIMESTAMPDIFF(MICROSECOND, accepted_at, activated_at) / 1000 AS delay_ms,
                      ROW_NUMBER() OVER (ORDER BY TIMESTAMPDIFF(MICROSECOND, accepted_at, activated_at)) AS rn
               FROM service
               WHERE accepted_at BETWEEN @start AND @end AND state = 'ACTIVE') ranked
           WHERE rn = @p95_rank), 999999)              AS p95_delay_ms,
       ROUND(AVG(CASE WHEN state = 'ACTIVE'
                 THEN TIMESTAMPDIFF(MICROSECOND, accepted_at, activated_at) / 1000 END)) AS avg_delay_ms,
       MAX(CASE WHEN state = 'ACTIVE'
                THEN TIMESTAMPDIFF(MICROSECOND, accepted_at, activated_at) / 1000 END)   AS max_delay_ms
FROM service
WHERE accepted_at BETWEEN @start AND @end;
