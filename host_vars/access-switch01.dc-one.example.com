---

access_interfaces:
  - type: "ge"
    fpc: 0
    id: 0
    mode: "layer3"
    ip4: 192.168.0.1/24
  - type: "ge"
    fpc: 0
    id: 1
    mode: "trunk"
    tagged_vlans:
      - 100
      - 200
      - 300
