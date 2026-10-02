-- Un schéma par module : chaque module possède ses données
CREATE DATABASE IF NOT EXISTS fleet;
CREATE DATABASE IF NOT EXISTS catalog;
CREATE DATABASE IF NOT EXISTS orders;

GRANT ALL PRIVILEGES ON fleet.*   TO 'candronex'@'%';
GRANT ALL PRIVILEGES ON catalog.* TO 'candronex'@'%';
GRANT ALL PRIVILEGES ON orders.*  TO 'candronex'@'%';

-- Module Drones : le seul endroit où l'IMSI existe
CREATE TABLE fleet.drone (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_id VARCHAR(32) NOT NULL,
    drone_id    VARCHAR(32) NOT NULL,
    imsi        CHAR(15)    NOT NULL,
    iccid       VARCHAR(20) NOT NULL,
    status      VARCHAR(16) NOT NULL,
    CONSTRAINT uq_drone_per_customer UNIQUE (customer_id, drone_id),
    CONSTRAINT uq_imsi  UNIQUE (imsi),
    CONSTRAINT uq_iccid UNIQUE (iccid)
);

-- Module Catalogue
CREATE TABLE catalog.service_specification (
    service_type       VARCHAR(16) PRIMARY KEY,
    service_name       VARCHAR(64) NOT NULL,
    sst                INT         NOT NULL,
    sd                 CHAR(6)     NOT NULL,
    dnn                VARCHAR(32) NOT NULL,
    five_qi            INT         NOT NULL,
    arp                INT         NOT NULL,
    ambr_uplink_mbps   INT         NOT NULL,
    ambr_downlink_mbps INT         NOT NULL
);

-- Module Commandes
CREATE TABLE orders.service_order (
    order_id        VARCHAR(32) PRIMARY KEY,
    customer_id     VARCHAR(32) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL,
    CONSTRAINT uq_idempotency_per_customer UNIQUE (customer_id, idempotency_key)
);

CREATE TABLE orders.service_order_item (
    item_id         VARCHAR(40) PRIMARY KEY,
    order_id        VARCHAR(32) NOT NULL,
    drone_id        VARCHAR(32) NOT NULL,     -- une simple référence : pas de clé étrangère vers fleet
    service_type    VARCHAR(16) NOT NULL,
    characteristics JSON        NOT NULL,     -- la copie figée du catalogue (le contrat)
    state           VARCHAR(16) NOT NULL,
    CONSTRAINT fk_item_order FOREIGN KEY (order_id) REFERENCES orders.service_order (order_id),
    CONSTRAINT uq_service_per_order UNIQUE (order_id, service_type)
);