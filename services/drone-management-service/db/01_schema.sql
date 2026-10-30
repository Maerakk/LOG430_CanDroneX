CREATE TABLE drone (
    id         BIGINT AUTO_INCREMENT PRIMARY KEY,
    client_id  VARCHAR(64) NOT NULL,
    drone_id   VARCHAR(32) NOT NULL,
    imsi       CHAR(15)    NOT NULL,
    iccid      VARCHAR(20) NOT NULL,
    status     VARCHAR(16) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT (UTC_TIMESTAMP(6)),
    CONSTRAINT uq_drone_per_client UNIQUE (client_id, drone_id),
    CONSTRAINT uq_imsi  UNIQUE (imsi),
    CONSTRAINT uq_iccid UNIQUE (iccid)
);
