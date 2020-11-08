# Ansible Juniper Automation Cookbook

This repository serves as a cookbook/skeleton für Juniper network device automation. It shows you how to...

- ...merge configuration snippets into your Juniper device
- ...query and evaluate the state of your Juniper device
- ...use a test driven approach to template development
- ...validate your `host_vars` and `group_vars` YAML files

However, it does not...

- ...try to be a guide to Juniper device configuration - the configuration snippets are only meant to illustrate the automation itself
- ...assume this is the only way to automate Juniper devices

**Some if not all aspects of this cookbook should also work with other network vendors.**

## Local Prerequisites

The content of this repository has been tested against Ansible 2.9 and 2.10. You need `ncclient` (the netconf client package) for the Juniper modules to work. To make your life easier, use Python 3 and a virtual environment for your Ansible setup:
```shell
apt install python3-virtualenv

mkdir -p ~/venv

virtualenv ~/venv/ansible-netconf
source ~/venv/ansible-netconf/bin/activate

pip install ansible ncclient netaddr
```

If you want to use YAML schema validation, we need the yamale package as well:
```shell
pip install yamale
```

If you want to use the test driven template development apporach, we need pytest and docker:
```shell
apt install docker.io
pip install pytest docker
```

You also need to build the junoser container image locally. The following command will retrieve the XSD configuration definition of the specified JunOS device (using `scp`) and build the image with it. You can optionally use the `-p` parameter to push the image to a specified docker registry, but you need to adapt the [testing code](tests/conftest.py) to reflect the image's location afterwards.

```shell
cd junoser-container
./build-docker-container.sh -d your-junos-device.example.com
```



This repository makes use of Ansible collections. To install all dependencies, navigate to the top directory of this repository and issue:
```shell
ansible-galaxy collection install -r collections/requirements.yml
```

## Remote Prerequisites

To start using Ansible you only need very few settings on your Juniper device:
- a minimal user configuration, e.g. `root` user with a password (do not forget to enable root login!)
- connectivity for your management interface (e.g. configure an IP address and set a default route if required)
- enable SSH + netconf:
```
set system services ssh 
set system services netconf ssh
```

If you use the `root` user for your initial deployment, **do not forget to disable root login after putting your real user configuration in place**! Ideally this would be part of your device's base configuration role in Ansible.

## How to Run a Playbook

If all requirements are met, you can simply run the following (don't forget to activate your virtual env!):
```shell
ansible-playbook -i inventory -u root -k access_switch.yml
```
This will asssume you want to login with `root` and it will ask you interactively for your password (`-k`). You can omit `-u` to use your local username instead and of cause also omit `-k` if you authenticate through other means (e.g. SSH keys).

You can limit the execution of your playbook using `-t` (only run tasks with a given tag) or `-l` (limit to a device group or certain devices):
```shell
# only deploy NTP and DNS configuration
ansible-playbook -i inventory -u root -k -t dns,ntp access_switch.yml

# only deploy access-switch01.dc-one.example.com
ansible-playbook -i inventory -u root -k -l access-switch01.dc-one.example.com access_switch.yml

# only deploy vlans to access switches in DC one
ansible-playbook -i inventory -u root -k -t vlans -l dc-one access_switch.yml
```

## Structure of This Repository

```shell
.
├── collections     # contains Ansible collection requirements file
├── group_vars      # Ansible group variables, e.g. common to a site/location
├── host_vars       # Ansible host variables, e.g. per device
├── roles           # Ansible roles
├── inventory       # Main inventory file for Ansible
└── *.yml           # Ansible playbooks for device configuration
```

## General Idea of Device Configuration

Instead of maintaining the entire device configuration in one single template, we make the use of multiple smaller templates. Juniper supports different strategies of applying configuration changes. We use `merge`, where the uploaded configuration gets merged into the currently running configuration. You can give hints to the parser so that it exclusively replaces a subsection but merged everything else: 
```
interfaces {
    replace:
    ge-0/0/0 {
        unit 0 {
            family inet {...}
        }
    }
}
```
The above example will be merged into the existing configuration (e.g. will keep all other interfaces) - but will make sure that the interface `ge-0/0/0` gets replaced with the new configuration. This has advantages as well as disadvantages:

- :heavy_plus_sign: smaller templates are easier to maintain and understand
- :heavy_plus_sign: reuse template code for multiple types of devices (e.g. use a common baseline configuration)
- :heavy_minus_sign: it is harder to remove parts of the configuration: if you remove e.g. an interface from your YAML data it will not be part of your template - but it will also not be removed from the device unless you use `replace` on the entire `interfaces` section (which might collide with other roles/templates also configuration interfaces). This is not impossible to solve, but will complicate your templates.
- :heavy_minus_sign: you need to carefully decidce where to use `replace` - otherwise your roles/templates might overwrite each other
- :warning: especially older devices tend to have long `commit` times - having many templates/commits in your playbooks will make the deployment a major pain. However, we use the `assemble` module of Ansible to merge all templates clientside before commiting which serves as a good workaround
  
## YAML Schema Validation

We use the `yamale` Python module to define schema files for our `host_vars` and `group_vars`. This way we can make sure to have all required variables present before we actually start the configuration deployment. Ansible is not able to detect missing variables before jinja2 tries to access them while rendering the templates (and hence will error out in the middle of your playbook run). At the same time, this will also help us to get rid of unused variables (e.g. which have been removed from templates but kept in the YAML structures). `yamale` also uses YAML to describe the structure/data in your real YAML files, which is documented [here](https://pypi.org/project/yamale/). It comes with predefined validators for basic types like integers, strings, lists, regexes, IP addresses etc.

### Integration into Playbooks

We use [this Ansible module](https://github.com/sipgate/ansible-module-yamale) to validate all YAML files as `pre_tasks` in our Playbooks. You can find examples for its usage in the [playbooks included in this repoyitory](access_switch.yml).

### Integration into Test Suites

You can also use a test suite like `pytest` to run schema validation tests - the offical [documentation](https://pypi.org/project/yamale/) has code examples available.

## Test Driven Template Development

We can use `pytest` and the Ruby gem `junoser` to locally validate and test jinja2 templates for Juniper devices. `junoser` will do the heavy lifting in this case:
- syntax-check the generated configuration
- convert to JunOS `set` syntax to have a normalized view for comparing

### How is this Test Driven?

We can establish a workflow along these lines:
- define/generate your configuration on a lab device (e.g. the `interfaces` block or only parts of it) and store this as the expected result
- build a template from this configuration and add it to one of your roles
- define sample data which can be used to render your template to the desired configuration in step 1
- integrate the new template into the testsuite

When the test passes and you need to change your configuration, follow these steps:
- adapt your desired configuration to the new needs (and hence break the test)
- adapt the template (and sample data) until the test passes

### Structure / Assumptions / How to Use?

- templates are stored as usual, e.g. `roles/${role-name}/templates/${template-name}.j2`
- sample data goes to: `tests/${role-name}/${template-name}.yml`
- reference/desired output goes to: `tests/${role-name}/${template-name}.conf`
- adapt [test_templates.py](tests/test_templates.py) to pick up your new template
- run `pytest` (or use the integrated pytest support in IDEs like PyCharm or Visual Studio Code)

### How does it work underneath?

The test definition in [test_templates.py](test_templates.py) runs the same procedure on all configured templates:
- read the YAML configuration file
- render the jinja2 template with the sample data to a temporary file
- syntax-check the rendered file with junoser
- convert both the rendered file and the stored reference configuration to the JunOS `set` syntax and do a string comparison

If any of the above steps fails, the test for the current template will fail.

