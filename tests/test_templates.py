import pytest

from tests.conftest import junos_config_test

access_switch_tests = [
    ("access/access-interfaces", "roles/access/templates/access-interfaces.j2"),
    ("access/vlans", "roles/access/templates/vlans.j2"),
]

edge_router_tests = [
    ("edge/transit", "roles/edge/templates/transit.j2")
]

@pytest.mark.parametrize("test_name, template_path", access_switch_tests)
def test_access_switch_templates(test_name, template_path, docker_client, template_engine):
    junos_config_test(docker_client, template_engine, test_name, template_path)


@pytest.mark.parametrize("test_name, template_path", edge_router_tests)
def test_edge_router_templates(test_name, template_path, docker_client, template_engine):
    junos_config_test(docker_client, template_engine, test_name, template_path)
