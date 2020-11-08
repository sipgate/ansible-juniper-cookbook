import os

import docker
import pytest
import yaml
import tempfile

from docker.errors import ContainerError
from jinja2 import Environment, BaseLoader, Template
try:
    # this is pre-ansible-collections
    from ansible.plugins.filter.ipaddr import ipaddr
except ModuleNotFoundError:
    # with 2.10, the ipaddr filter has moved to the netcommon collection
    from ansible_collections.ansible.netcommon.plugins.filter.ipaddr import ipaddr


@pytest.fixture
def docker_client(scope="session"):
    client = docker.from_env()
    return client


@pytest.fixture(scope="session")
def template_engine():
    jinja2_environment = Environment(
        loader=BaseLoader()
    )
    # add custom filters which ansible adds to jinja,
    # but are not present in plain jinja2
    jinja2_environment.filters["ipaddr"] = ipaddr

    return jinja2_environment


def read_file(file):
    with open(file) as f:
        file_content = f.read()

    return file_content


def parse_yaml(file):
    with open(file) as c:
        file = yaml.load(c, Loader=yaml.FullLoader)

    return file


def write_tmp_file(file_content):
    _, path = tempfile.mkstemp()
    with open(path, "w") as result_path:
        result_path.write(file_content)

    return path


def validate_junos_config(docker_client, config_path):
    try:
        docker_client.containers.run('junos-config-validator',
                                     command="/junoser/exe/junoser -c /generated.txt",
                                     volumes={config_path: {'bind': '/generated.txt', 'mode': 'ro'}})
    except ContainerError as e:
        pytest.fail("Config check of template {} failed: {}".format(config_path, e))


def convert_junos_config_to_set(docker_client, config_path):
    set_syntax_result = docker_client.containers.run('junos-config-validator',
                                                     command="/junoser/exe/junoser -d /generated.txt",
                                                     volumes={config_path: {'bind': '/generated.txt', 'mode': 'ro'}})

    return set_syntax_result


def junos_config_test(docker_client, template_engine, test_name, template_path):
    configuration_path = "tests/{0}.yml".format(test_name)
    expected_result_path = "tests/{0}.conf".format(test_name)
    expected_result_absolute_path = os.path.abspath(expected_result_path)
    template = read_file(template_path)

    # remove "replace:" lines from template text
    # junoser does not understand this syntax
    template = template.replace("replace:", "")

    # read config from yaml file into python dictionary
    configuration = parse_yaml(configuration_path)

    # parse template with jinja2
    validatable_template = template_engine.from_string(template)

    # feed configuration dictionary to template renderer
    rendered_template = validatable_template.render(**configuration)
    rendered_template_path = write_tmp_file(rendered_template)

    # validate configuration
    validate_junos_config(docker_client, rendered_template_path)
    validate_junos_config(docker_client, expected_result_absolute_path)

    # convert configuration to set syntax
    set_syntax_result = convert_junos_config_to_set(docker_client, rendered_template_path)
    set_syntax_expected_result = convert_junos_config_to_set(docker_client, expected_result_absolute_path)
    assert set_syntax_result.decode("utf-8") == set_syntax_expected_result.decode("utf-8")

    os.remove(rendered_template_path)
