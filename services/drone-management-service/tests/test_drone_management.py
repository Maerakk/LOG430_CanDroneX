import time

import jwt
import pytest

from candronex_common.errors import InvalidValueError
from candronex_common.testing import OTHER_KEY, auth_headers, token, verifier
from drone_management.adapter.outbound.in_memory import InMemoryDroneRepository
from drone_management.application.use_cases import RegisterDrone
from drone_management.domain.errors import DroneAlreadyRegisteredError, NetworkIdentityUnavailableError
from drone_management.domain.model import DroneId, Iccid, Imsi
from drone_management.main import create_app

DRONE = {"droneId": "DRN-0231", "imsi": "302720000010231", "iccid": "8930272000000010231"}


@pytest.mark.parametrize("value", ["30272000001023", "3027200000102311", "30272000001023a", "３０２７２００００１０２３１"])
def test_invalid_imsi_is_refused(value):
    with pytest.raises(InvalidValueError):
        Imsi(value)


def test_imsi_is_masked():
    assert Imsi("302720000010231").masked() == "30272******0231"


@pytest.mark.parametrize("value", ["893027200000001023", "893027200000001023123"])
def test_invalid_iccid_is_refused(value):
    with pytest.raises(InvalidValueError):
        Iccid(value)


@pytest.mark.parametrize("value", ["AB", "x" * 33, "DRN 01", "DRN_01"])
def test_invalid_drone_id_is_refused(value):
    with pytest.raises(InvalidValueError):
        DroneId(value)


@pytest.fixture
def register():
    return RegisterDrone(InMemoryDroneRepository())


def test_register_drone(register):
    drone, created = register.execute(DRONE["droneId"], DRONE["imsi"], DRONE["iccid"], "inspectra-demo")
    assert created and drone.is_eligible()


def test_replaying_the_same_registration_returns_the_drone(register):
    register.execute(DRONE["droneId"], DRONE["imsi"], DRONE["iccid"], "inspectra-demo")
    _, created = register.execute(DRONE["droneId"], DRONE["imsi"], DRONE["iccid"], "inspectra-demo")
    assert not created


def test_same_drone_id_with_another_identity_is_a_conflict(register):
    register.execute(DRONE["droneId"], DRONE["imsi"], DRONE["iccid"], "inspectra-demo")
    with pytest.raises(DroneAlreadyRegisteredError):
        register.execute(DRONE["droneId"], "302720000099999", DRONE["iccid"], "inspectra-demo")


def test_imsi_used_by_another_client_is_refused(register):
    register.execute(DRONE["droneId"], DRONE["imsi"], DRONE["iccid"], "inspectra-demo")
    with pytest.raises(NetworkIdentityUnavailableError):
        register.execute("AERO-1", DRONE["imsi"], "8930272000000099999", "aerotech-demo")


@pytest.fixture
def client():
    return create_app(InMemoryDroneRepository(), verifier()).test_client()


URL = "/api/drone-management/v1/drone"


def test_rest_register_then_replay(client):
    first = client.post(URL, json=DRONE, headers=auth_headers())
    assert first.status_code == 201
    assert first.json["imsi"] == "30272******0231"
    assert first.headers["Location"] == f"{URL}/DRN-0231"
    assert client.post(URL, json=DRONE, headers=auth_headers()).status_code == 200


@pytest.mark.parametrize("auth", [
    None, "Basic abc", "Bearer abc.def.ghi",
    token(exp=int(time.time()) - 10),            # expiré
    token(aud="account"),                       # mauvaise audience
    token(iss="http://localhost:8081/realms/master"),
    token(key=OTHER_KEY),                       # signature d'une autre clé
    "Bearer " + jwt.encode({"azp": "x", "aud": "candronex-api"}, None, algorithm="none"),
])
def test_rest_refuses_calls_without_a_valid_token(client, auth):
    headers = {"Authorization": auth} if auth else {}
    r = client.post(URL, json=DRONE, headers=headers)
    assert r.status_code == 401
    assert r.content_type == "application/problem+json"
    assert client.get(URL, headers=auth_headers()).json == []


def test_forged_client_header_does_not_replace_the_token(client):
    client.post(URL, json=DRONE, headers=auth_headers("inspectra-demo"))
    r = client.get(URL, headers=auth_headers("aerotech-demo", **{"X-Client-Id": "inspectra-demo"}))
    assert r.json == []


def test_rest_other_client_cannot_see_the_drone(client):
    client.post(URL, json=DRONE, headers=auth_headers("inspectra-demo"))
    r = client.get(f"{URL}/DRN-0231", headers=auth_headers("aerotech-demo"))
    assert r.status_code == 404
    assert "302720000010231" not in r.get_data(as_text=True)
    assert client.get(f"{URL}/DRN-0231/networkIdentity", headers=auth_headers("aerotech-demo")).status_code == 404


@pytest.mark.parametrize("body", [None, [], {"droneId": "DRN-1"}, {**DRONE, "imsi": 302720000010231}])
def test_rest_malformed_request_is_400(client, body):
    r = client.post(URL, json=body, headers=auth_headers())
    assert r.status_code == 400


def test_rest_business_rule_is_422_with_full_problem_details(client):
    r = client.post(URL, json={**DRONE, "imsi": "123"}, headers=auth_headers(**{"X-Correlation-Id": "cmd-42"}))
    assert r.status_code == 422
    assert set(r.json) >= {"type", "title", "status", "detail", "instance"}
    assert r.json["instance"] == URL
    assert r.headers["X-Correlation-Id"] == "cmd-42"


def test_network_identity_is_only_given_to_the_owner(client):
    client.post(URL, json=DRONE, headers=auth_headers())
    r = client.get(f"{URL}/DRN-0231/networkIdentity", headers=auth_headers())
    assert r.json == {"droneId": "DRN-0231", "imsi": "302720000010231", "eligible": True}
