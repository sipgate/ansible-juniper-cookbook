#!/bin/bash -e

usage() {
    echo "This script will download the XSD Schema definition from a JunOS Device and build a junoser container image with it."
    echo
    echo "  -h             This help output"
    echo "  -f             Force a new download of the junos.xsd (otherwise an existing one will be used)"
    echo "  -d [hostname]  Specify the JunOS device to retrieve the XSD schema from"
    echo "  -p [registry]  Publish the container image to [registry] (e.g. registry.example.com/junos-config-validator)"
}

DOCKER_REGISTRY=""
JUNOS_DEVICE=""
FORCE_XSD="no"

while getopts "hfd:p:" opt; do
    case $opt in
            h)
                    usage
                    exit 0
                    ;;
            f)
                    FORCE_XSD="yes"
                    ;;
            d)
                    JUNOS_DEVICE=$OPTARG
                    ;;
            p)
                    DOCKER_REGISTRY=$OPTARG
                    ;;
    esac
done

if [ -z "$JUNOS_DEVICE" ]; then
    echo "Please specify a Juniper Device to retrieve the XSD schema from"
    exit 1
fi

# pull xsd from JunOS Device
if [ -f junos.xsd -a "$FORCE_XSD" = "no" ]; then
    echo "junos.xsd already exists and -f is not set, using this one for the container"
else
    ssh -Csp 830 ${JUNOS_DEVICE} netconf < ./rpc-get-schema.xml | sed -n '/^<xsd:schema/,/^<\/xsd:schema/p' > junos.xsd
fi

# build image
docker build -t junos-config-validator .

# upload image to repository
if [ -n "$DOCKER_REGISTRY" ]; then
    docker tag junos-config-validator ${DOCKER_REGISTRY}
    docker push ${DOCKER_REGISTRY}
fi