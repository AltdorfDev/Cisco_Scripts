#!/usr/bin/env python3
"""
Script de configuracion para R1, R2 y R3 usando Netmiko.
Topologia: R1 -- R3 -- R2 (R3 en el medio, sin LAN propia)
  R1(g3/0)=LAN 10.10.10.0/24      R1(g2/0)=192.168.12.1 <-> R3(g2/0)=192.168.12.2
  R2(g3/0)=LAN 172.16.2.0/24      R2(g1/0)=192.168.23.2 <-> R3(g1/0)=192.168.23.1

Configura:
  - Interfaces LAN/WAN
  - DHCP (R1 y R2, R3 solo enruta y no tiene LAN)
  - OSPF (Process ID 123) con conectividad completa entre los 3 routers

Credenciales tomadas de variables de entorno para no exponerlas en el script:
  export NET_USER="admin"
  export NET_PASS="cisco123"
"""

import os
from netmiko import ConnectHandler

# --- Credenciales desde variables de entorno ---
USERNAME = os.environ.get("NET_USER")
PASSWORD = os.environ.get("NET_PASS")

if not USERNAME or not PASSWORD:
    raise SystemExit("Error: defina las variables de entorno NET_USER y NET_PASS antes de ejecutar el script.")

# --- Datos de conexion de cada dispositivo ---
r1 = {
    "device_type": "cisco_ios",
    "host": "192.168.100.76",
    "username": USERNAME,
    "password": PASSWORD,
}

r2 = {
    "device_type": "cisco_ios",
    "host": "192.168.100.77",
    "username": USERNAME,
    "password": PASSWORD,
}

r3 = {
    "device_type": "cisco_ios",
    "host": "192.168.100.78",
    "username": USERNAME,
    "password": PASSWORD,
}

# --- Comandos de configuracion para R1 ---
# g3/0 = LAN de R1 (10.10.10.0/24) con DHCP (excluyendo las primeras 9 IP)
# g2/0 = enlace hacia R3 (192.168.12.0/24)
# OSPF process-id 123, Router ID 0.0.0.1, se anuncian ambas redes directamente conectadas
r1_config = [
    # Interfaz LAN
    "interface g3/0",
    "ip address 10.10.10.1 255.255.255.0",
    "no shutdown",
    "exit",
    # Interfaz hacia R3
    "interface g2/0",
    "ip address 192.168.12.1 255.255.255.0",
    "no shutdown",
    "exit",
    # DHCP para la LAN de R1, excluyendo las primeras 9 direcciones (10.10.10.1 - 10.10.10.9)
    "ip dhcp excluded-address 10.10.10.1 10.10.10.9",
    "ip dhcp pool LAN_R1",
    "network 10.10.10.0 255.255.255.0",
    "default-router 10.10.10.1",
    "exit",
    # OSPF
    "router ospf 123",
    "router-id 0.0.0.1",
    "network 10.10.10.0 0.0.0.255 area 0",
    "network 192.168.12.0 0.0.0.255 area 0",
    "exit",
]

# --- Comandos de configuracion para R2 ---
# g3/0 = LAN de R2 (172.16.2.0/24) con DHCP (excluyendo las primeras 9 IP)
# g1/0 = enlace hacia R3 (192.168.23.0/24)
r2_config = [
    # Interfaz LAN
    "interface g3/0",
    "ip address 172.16.2.1 255.255.255.0",
    "no shutdown",
    "exit",
    # Interfaz hacia R3
    "interface g1/0",
    "ip address 192.168.23.2 255.255.255.0",
    "no shutdown",
    "exit",
    # DHCP para la LAN de R2, excluyendo las primeras 9 direcciones (172.16.2.1 - 172.16.2.9)
    "ip dhcp excluded-address 172.16.2.1 172.16.2.9",
    "ip dhcp pool LAN_R2",
    "network 172.16.2.0 255.255.255.0",
    "default-router 172.16.2.1",
    "exit",
    # OSPF
    "router ospf 123",
    "router-id 0.0.0.2",
    "network 172.16.2.0 0.0.0.255 area 0",
    "network 192.168.23.0 0.0.0.255 area 0",
    "exit",
]

# --- Comandos de configuracion para R3 ---
# g2/0 = enlace hacia R1 (192.168.12.0/24)
# g1/0 = enlace hacia R2 (192.168.23.0/24)
# R3 no tiene LAN ni DHCP, solo enruta entre R1 y R2
r3_config = [
    # Interfaz hacia R1
    "interface g2/0",
    "ip address 192.168.12.2 255.255.255.0",
    "no shutdown",
    "exit",
    # Interfaz hacia R2
    "interface g1/0",
    "ip address 192.168.23.1 255.255.255.0",
    "no shutdown",
    "exit",
    # OSPF
    "router ospf 123",
    "router-id 0.0.0.3",
    "network 192.168.12.0 0.0.0.255 area 0",
    "network 192.168.23.0 0.0.0.255 area 0",
    "exit",
]

# --- Lista de routers a configurar: (datos_conexion, lista_comandos, nombre) ---
dispositivos = [
    (r1, r1_config, "R1"),
    (r2, r2_config, "R2"),
    (r3, r3_config, "R3"),
]

# --- Conexion y envio de configuracion a cada router ---
for datos_conexion, comandos, nombre in dispositivos:
    print(f"Conectando a {nombre} ({datos_conexion['host']})...")
    try:
        conexion = ConnectHandler(**datos_conexion)

        # cmd_verify=False evita que Netmiko espere el eco exacto de cada
        # comando antes de continuar (esto es lo que provoca ReadTimeout
        # cuando una interfaz no existe, hay banners, o el prompt cambia).
        # read_timeout mas alto da margen si el equipo responde lento.
        salida = conexion.send_config_set(comandos, cmd_verify=False, read_timeout=30)
        print(salida)

        conexion.save_config()  # equivalente a "write memory"
        print(f"Configuracion aplicada correctamente en {nombre}.")
        conexion.disconnect()

    except Exception as error:
        # Si un router falla, se informa el error y se continua con el siguiente
        print(f"ERROR al configurar {nombre}: {error}")

print("Configuracion finalizada.")
