import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "mysql+pymysql://candronex:candronex@127.0.0.1:3310")
TEST_CUSTOMER = "CUST-TEST"


@pytest.fixture
def session_factory():
    engine = create_engine(TEST_DATABASE_URL)

    # Si MySQL n'est pas lancé, on saute les tests au lieu de les faire échouer
    try:
        with engine.connect():
            pass
    except OperationalError:
        pytest.skip("MySQL n'est pas disponible : lance d'abord 'docker compose up -d db'")

    yield sessionmaker(bind=engine)          # ← le test s'exécute ici

    # Après le test : on supprime seulement les données du client de test
    with engine.begin() as connection:
        connection.execute(text(
            "DELETE FROM orders.service_order_item WHERE order_id IN "
            "(SELECT order_id FROM orders.service_order WHERE customer_id = :c)"), {"c": TEST_CUSTOMER})
        connection.execute(text("DELETE FROM orders.service_order WHERE customer_id = :c"), {"c": TEST_CUSTOMER})
        connection.execute(text("DELETE FROM fleet.drone WHERE customer_id = :c"), {"c": TEST_CUSTOMER})
    engine.dispose()