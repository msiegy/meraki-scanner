import meraki
import os
from dotenv import load_dotenv

# Set your API key and organization ID
load_dotenv()
API_KEY = os.environ.get('MerakiAPIKey')
ORG_ID = os.environ.get('organizationId')
NETWORKS = [os.environ.get('networks')]
ms_firmware_level = 'switch-15-21-1'

# Initialize the Meraki API client
dashboard = meraki.DashboardAPI(API_KEY)

def get_firmware_versions():
    # Get all devices in the organization
    networks = dashboard.organizations.getOrganizationNetworks(ORG_ID)

    firmware_versions = {}
        
    # Iterate over each network (by device would be messy)
    for network in NETWORKS:
        firmware = dashboard.networks.getNetworkFirmwareUpgrades(network)

        # Check if firmware information is available, then store firmware version in dictionary by network key
        if 'products' in firmware:
            version = firmware['products']['switch']['currentVersion']['firmware']
            firmware_versions[network] = version

    return firmware_versions

def get_switch_ports():
    # Get all devices in the organization
    devices = dashboard.organizations.getOrganizationDevices(ORG_ID)

    switch_ports = {}

    # Iterate over each device
    for device in devices:
        serial = device['serial']
        ports = dashboard.switch.getDeviceSwitchPorts(serial)

        # Check if switch port information is available
        if 'ports' in ports:
            switch_ports[serial] = ports['ports']

    return switch_ports

def check_firmware_versions():
    firmware_versions = get_firmware_versions()

    for network, version in firmware_versions.items():
        if version != ms_firmware_level:
            print(f"Network {network} has firmware version {version}, which is not equal to desired version {ms_firmware_level}.")
        else:
            print(f"Network {network} meets requirements with firmware version {version}")                  
                  
def check_switch_port_config():
    switch_ports = get_switch_ports()

    for serial, ports in switch_ports.items():
        for port in ports:
            if port['accessPolicyType'] != 'closed':
                print(f"Port {port['portId']} on device with serial {serial} is not configured with accessPolicyType = closed.")

# Run the checks
check_firmware_versions()
#check_switch_port_config()

#import ipdb
#ipdb.set_trace() 