import meraki
import os
import requests
from colorama import Fore, Back, Style
from pprint import pprint 
from dotenv import load_dotenv

"""
- Pull down Running Meraki Device Firmware information for all devices in a given Organization ID from the Meraki Cloud API.
- Pull down Vulnerability CVEs for Meraki platforms from the OpenVulnAPI
- [TODO] Check network devices for required security configuration
- [TODO] Compile Data for routine batch Kenna Upload
"""

# Set your API key and organization ID
load_dotenv()
API_KEY = os.environ.get('MerakiAPIKey')
ORG_ID = os.environ.get('organizationId')
NETWORKS = [os.environ.get('networks')]
VULNCLIENTID = [os.environ.get('openvulnCLIENT_ID')]
VULNSECRET = [os.environ.get('openvulnCLIENT_SECRET')]
ms_firmware_level = 'switch-15-21-1'

#resourceIDs=204722 (MS), 204723 (MR), 204724 (MX)
MSfamily = "Cisco%20Meraki%20MS%20Firmware"
MRfamily = "Cisco%20Meraki%20MR%20Firmware"
MXfamily = "Cisco%20Meraki%20MX%20Firmware"

# Initialize the Meraki API client
dashboard = meraki.DashboardAPI(API_KEY)

def get_firmware_versions():
    # Get all devices in the organization
    networks = dashboard.organizations.getOrganizationNetworks(ORG_ID)  #not used for testing, change loop reference below to leverage.

    firmware_versions = {}
        
    # Iterate over each network (by device would be messy)
    for network in NETWORKS:
        firmware = dashboard.networks.getNetworkFirmwareUpgrades(network)
        #import ipdb; ipdb.set_trace()

        # Check if firmware information is available, then store firmware version in dictionary by network key
        if 'products' in firmware:
            version = firmware['products']['switch']['currentVersion']['firmware']
            firmware_versions[network] = version

    print("\n\n Raw Firmware Versions\n",firmware_versions,"\n\n")
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

def get_firmware_by_device():
    firmwarebydevice = []

    response = dashboard.organizations.getOrganizationFirmwareUpgradesByDevice(ORG_ID, total_pages='all')

    for device in response:
        if device['deviceStatus'] == "Completed":   #skip entries for "started"
            serial = device['serial']
            deviceinfo = dashboard.devices.getDevice(serial)
            #print(deviceinfo['firmware'], '  ', device['upgrade']['toVersion']['shortName'])
            firmwarebydevice.append({'serial': device['serial'],
                                    'hostname': device['name'],
                                    'firmware': device['upgrade']['toVersion']['shortName'],
                                    'ipAddress': deviceinfo['lanIp'],
                                    'model': deviceinfo['model']
                                    })
    
    return firmwarebydevice
                  
def check_switch_port_config():
    switch_ports = get_switch_ports()

    for serial, ports in switch_ports.items():
        for port in ports:
            if port['accessPolicyType'] != 'closed':
                print(f"Port {port['portId']} on device with serial {serial} is not configured with accessPolicyType = closed.")

def get_vuln_auth_token():
    url="https://id.cisco.com/oauth2/default/v1/token"
    data = {
        'grant_type': 'client_credentials',
        'client_secret': VULNSECRET,
        'client_id': VULNCLIENTID
    }
    response=requests.post(url, data=data).json()
    token_string=response['access_token']

    return token_string
    
def check_open_vulns(productfamily):
    token = get_vuln_auth_token()
    headers = {"Authorization": "Bearer " + token}
    response = requests.get('https://apix.cisco.com/security/advisories/v2/product?product='+productfamily, headers=headers)

    response = response.json()
    return response
 

# Run the checks
#check_firmware_versions()
#get_firmware_versions()

firmwaredata= get_firmware_by_device()
vulnerabilities = check_open_vulns(MSfamily)

print(Fore.GREEN, "#######- MERAKI RUNNING FIRMWARE INFORMATION -#######\n")
pprint(firmwaredata)
input() #wait for user input to continue, for demo.
print(Fore.RED, "\n\n#######- MERAKI VULNERABILITY INFORMATION -#######\n")
print("OpenVuln API returned", len(vulnerabilities['advisories']), "vulnerabilities to investigate:")
for advisory in vulnerabilities['advisories']:
    print(" ", advisory['advisoryId'])
input() #wait for user input to continue, for demo.

pprint(vulnerabilities)
#import ipdb; ipdb.set_trace()
#check_switch_port_config()
