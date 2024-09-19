import meraki
import os
import json
#from colorama import Fore, Back, Style
#from pprint import pprint
from dotenv import load_dotenv

"""
INSTALL:
- git clone https://github.com/msiegy/meraki-scanner.git && cd meraki-scanner
- python -m venv venv && source venv/bin/activate
- pip install -r requirements.txt
- Update MerakiAPIKey in .env file and update org_id and network_ids values below.
- Run compare_firmware.py

SCRIPT:
- Pull down Running Meraki Device Firmware information for all devices in a given Organization ID from the Meraki Cloud API.
- Pull down latest available versions for provided product families.
- Compare Running Firmware against Latest available and Compile JSON Data for routine batch Kenna Upload
- [TODO] Pull down Vulnerability CVEs for Meraki platforms from the OpenVulnAPI
- [TODO] Check network devices for required security configuration
"""

# Set your API key from secrets
load_dotenv()
API_KEY = os.environ.get('MerakiAPIKey')

# User-defined network IDs, product families, and desired release type
org_id = 'your_organization_id'  # Replace with your actual organization ID
network_ids = ['your_network_IDs']  # Replace with actual network IDs
product_families = ['switch', 'switchCatalyst']
desired_release_type = 'candidate'  # User-defined release type (e.g., 'stable', 'candidate', beta, etc)

# Instantiate the Meraki dashboard API
dashboard = meraki.DashboardAPI(API_KEY)

def get_product_family(device_model):
    # Dictionary mapping model prefixes to product families
    prefix_map = {
        'MS': 'switch',
        'C9': 'switchCatalyst',
        'MR': 'wireless',
        'MV': 'camera'
    }
    
    # Return the corresponding product family or 'unknown' if not found
    return next((family for prefix, family in prefix_map.items() if device_model.startswith(prefix)), 'unknown')

# Function to get firmware details for a given network ID and product family
def get_latest_firmware_info(network_id, product_families, desired_release_type):
    firmware_info = {}
    
    try:
        # Fetch firmware upgrade information for the network
        firmware_upgrades = dashboard.networks.getNetworkFirmwareUpgrades(network_id)
        
        # Iterate over the product families of interest
        for product_family in product_families:
            available_versions = firmware_upgrades.get('products', {}).get(product_family, {}).get('availableVersions', [])
            
            # Filter versions based on the desired release type
            stable_versions = [version for version in available_versions if version.get('releaseType') == desired_release_type]
            
            # If versions exist for the desired release type, fetch the latest one
            if stable_versions:
                latest_version = stable_versions[-1]  # Assuming the last one is the latest
                short_name = latest_version.get('shortName', 'N/A')
                release_date = latest_version.get('releaseDate', 'N/A')
                
                firmware_info[product_family] = {
                    'product_family': product_family,
                    'latest_short_name': short_name,
                    'release_date': release_date,
                    'release_type': desired_release_type
                }
            else:
                # If no versions are available for the desired release type, set as 'N/A'
                firmware_info[product_family] = {
                    'product_family': product_family,
                    'latest_short_name': 'N/A',
                    'release_date': 'N/A',
                    'release_type': 'N/A'
                }
    
    except Exception as e:
        # Handle any exception and store the error message
        firmware_info['error'] = str(e)
    
    return firmware_info

# Function to get the currently running firmware versions for devices of the defined product families
def get_current_firmware_versions(org_id, product_families):
    device_info = {}
    seen_serials = set()
    
    try:
        # Fetch firmware upgrade information by device in the organization
        devices = dashboard.organizations.getOrganizationFirmwareUpgradesByDevice(org_id, upgradeStatuses='Completed')
        
        # Sort devices by timestamp in descending order to get the latest upgrades first
        devices.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Loop through devices to store current firmware shortName and model type, filtering by product family
        for device in devices:
            serial = device.get('serial', 'N/A')
            
            # Skip if we've already processed this serial
            if serial in seen_serials:
                continue
            
            seen_serials.add(serial)
            
            deviceinfo = dashboard.devices.getDevice(serial)
            model = deviceinfo['model']
            ipAddress = deviceinfo['lanIp']
            hostname = deviceinfo['name']
            short_name = device.get('upgrade').get('toVersion').get('shortName', 'N/A')
            
            # Map models to product families based on user-defined product families
            product_family = get_product_family(model)
            
            # Store the device's current firmware info if it matches the product family
            device_info[serial] = {
                'model': model,
                'running_firmware': short_name,  # Using the shortName from toVersion
                'product_family': product_family,
                'ipAddress': ipAddress,
                'hostname': hostname
            }
            
    except Exception as e:
        # Handle any exceptions
        device_info['error'] = str(e)
    
    return device_info


# Function to merge and compare current vs latest firmware versions
def compare_firmware_versions(network_ids, org_id, product_families, desired_release_type):
    comparison_results = {}
    
    for network_id in network_ids:
        # Get latest firmware info for product families
        latest_firmware_info = get_latest_firmware_info(network_id, product_families, desired_release_type)
        
        # Get current firmware running on devices, filtered by product families
        current_firmware_info = get_current_firmware_versions(org_id, product_families)
        
        # Compare the two and store results
        comparison_results[network_id] = {}
        
        for serial, device_info in current_firmware_info.items():
            # Ensure device_info is a dictionary (skip errors if any)
            if not isinstance(device_info, dict):
                continue

            product_family = device_info.get('product_family', 'unknown')
            
            # Get the latest firmware for the product family
            latest_firmware = latest_firmware_info.get(product_family, {})
            latest_version = latest_firmware.get('latest_short_name', 'N/A')
            
            # Compare current firmware shortName (from the running version) with the latest version available
            comparison_results[network_id][serial] = {
                'hostname': device_info.get('hostname', 'N/A'),
                'ipAddress': device_info.get('ipAddress', 'N/A'),
                'model': device_info.get('model', 'N/A'),
                'running_firmware': device_info.get('running_firmware', 'N/A'),
                #'running_release_type': device_info.get('release_type', 'N/A'),
                'latest_firmware': latest_version,
                'desired_release_type': latest_firmware.get('release_type', 'N/A'),
                'up_to_date': device_info.get('running_firmware', '').endswith(latest_version)  # Compare the end part of the running firmware with the latest shortName
            }
    
    # Output the results as JSON
    return json.dumps(comparison_results, indent=4)

# Call the function and print the comparison results
print(compare_firmware_versions(network_ids, org_id, product_families, desired_release_type))
