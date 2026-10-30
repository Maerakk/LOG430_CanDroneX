CREATE TABLE service_specification (
    id               VARCHAR(64)  PRIMARY KEY,
    name             VARCHAR(128) NOT NULL,
    slice_type       VARCHAR(16)  NOT NULL,
    lifecycle_status VARCHAR(16)  NOT NULL
);

CREATE TABLE service_spec_characteristic (
    specification_id VARCHAR(64) NOT NULL,
    name             VARCHAR(32) NOT NULL,
    position         INT         NOT NULL,
    value_type       VARCHAR(16) NOT NULL,
    value            VARCHAR(64) NOT NULL,
    PRIMARY KEY (specification_id, name),
    CONSTRAINT fk_characteristic_spec FOREIGN KEY (specification_id) REFERENCES service_specification (id)
);

CREATE TABLE service_order (
    order_id        VARCHAR(32) PRIMARY KEY,
    client_id       VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    accepted_at     DATETIME(6) NOT NULL,
    CONSTRAINT uq_idempotency_per_client UNIQUE (client_id, idempotency_key)
);

-- drone_id et service_id référencent les autres services, sans clé étrangère
CREATE TABLE service_order_item (
    item_id            VARCHAR(40)  PRIMARY KEY,
    order_id           VARCHAR(32)  NOT NULL,
    client_id          VARCHAR(64)  NOT NULL,
    action             VARCHAR(16)  NOT NULL,
    drone_id           VARCHAR(32)  NOT NULL,
    specification_id   VARCHAR(64)  NOT NULL,
    specification_name VARCHAR(128) NOT NULL,
    characteristics    JSON         NOT NULL,
    service_id         VARCHAR(40)  NULL,
    state              VARCHAR(16)  NOT NULL,
    CONSTRAINT fk_item_order FOREIGN KEY (order_id) REFERENCES service_order (order_id),
    CONSTRAINT uq_specification_per_order UNIQUE (order_id, specification_id),
    INDEX ix_item_blocking (client_id, drone_id, specification_id, state)
);
