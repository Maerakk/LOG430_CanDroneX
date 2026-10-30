CREATE TABLE service (
    service_id       VARCHAR(40)  PRIMARY KEY,
    client_id        VARCHAR(64)  NOT NULL,
    order_id         VARCHAR(32)  NOT NULL,
    order_item_id    VARCHAR(40)  NOT NULL,
    drone_id         VARCHAR(32)  NOT NULL,
    imsi             CHAR(15)     NOT NULL,
    specification_id VARCHAR(64)  NOT NULL,
    characteristics  JSON         NOT NULL,
    state            VARCHAR(16)  NOT NULL,
    accepted_at      DATETIME(6)  NOT NULL,
    activated_at     DATETIME(6)  NULL,
    failure_reason   VARCHAR(128) NULL,
    attempts         INT          NOT NULL,
    CONSTRAINT uq_service_per_order_item UNIQUE (order_item_id),
    INDEX ix_service_order (client_id, order_id),
    INDEX ix_service_accepted (accepted_at)
);
