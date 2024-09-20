import meraki
import os
import json
from dotenv import load_dotenv

"""
INSTALL:
- git clone https://github.com/msiegy/meraki-scanner.git && cd meraki-scanner
- python -m venv venv && source venv/bin/activate
- pip install -r requirements.txt
- Configure MerakiAPIKey ENV variable and update org_id and network_id values below.
- Run compare_firmware.py

SCRIPT:
- Pull down Running Meraki Device Firmware information for all devices in multiple Organization IDs using getOrganizationFirmwareUpgradesByDevice.
- Pull down latest available versions for provided product families, using getNetworkFirmwareUpgrades on a network containing relevant devices.
- Compare Running Firmware against Latest available and Compile JSON Data for routine batch Kenna Upload
- [TODO] Add logic to allow exluding specific network_IDs. e.g.: Labs, etc.
- [TODO] Pull down Vulnerability CVEs for Meraki platforms from the OpenVulnAPI
- [TODO] Check network devices for required security configuration
"""

# Set your API key from secrets
load_dotenv()
API_KEY = os.environ.get('MerakiAPIKey')

# User-defined organization IDs, network IDs, product families, and desired release type
org_ids = ['your_org_id'] # Replace with your actual organization ID
network_id = 'your_network_id' # Replace with actual network ID. Only used to fetch latest firmware versions available.  
product_families = ['switch', 'switchCatalyst']
desired_release_type = 'stable'  # User-defined release type (e.g., 'stable', 'candidate', beta, etc.)

# Instantiate the Meraki dashboard API
dashboard = meraki.DashboardAPI(API_KEY)

# Function to compare versions and handle varying naming schemes. If running version is greater or equal to latest, return True
def compare_versions(running_firmware, latest_version):
    # Extract numeric parts of the version (ignoring the prefix like 'MS')
    running_version_parts = [int(part) for part in running_firmware.split()[-1].split('.') if part.isdigit()]
    latest_version_parts = [int(part) for part in latest_version.split()[-1].split('.') if part.isdigit()]

    # Compare the version parts; return True if running version is greater or equal, it's considered up to date
    return running_version_parts >= latest_version_parts

def get_product_family(device_model):
    # Dictionary mapping model prefixes to product families. Used to pull latest firmware available for the appropriate product family. e.g.: MS390 will consider 'switch' product family releases.
    prefix_map = {
        'MS': 'switch',
        'C9': 'switchCatalyst',
        'MR': 'wireless',
        'MV': 'camera'
    }
    
    # Return the corresponding product family or 'unknown' if not found
    return next((family for prefix, family in prefix_map.items() if device_model.startswith(prefix)), 'unknown')

# Function to get the latest available firmware version and details for a given network ID and product family
def get_latest_firmware_info(network_id, product_families, desired_release_type):
    firmware_info = {}
    
    try:
        # Fetch firmware upgrade information for the network
        firmware_upgrades = dashboard.networks.getNetworkFirmwareUpgrades(network_id)
        
        # Iterate over the product families of interest
        for product_family in product_families:
            available_versions = firmware_upgrades.get('products', {}).get(product_family, {}).get('availableVersions', [])
            
            # Filter versions based on the desired release type
            desired_versions = [version for version in available_versions if version.get('releaseType') == desired_release_type]
            
            # If versions exist for the desired release type, fetch the latest one
            if desired_versions:
                latest_version = desired_versions[-1]  # Assuming the last one is the latest
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
        if '404' in str(e):
         print(f"ERROR: 404 Not Found. Please ensure the network ID '{network_id}' is correct and contains devices of the specified product families.")
        else:
            print(f"ERROR: {e}")
        firmware_info['error'] = str(e)
    
    return firmware_info

# Function to get the currently running firmware versions for devices of the defined product families
def get_current_firmware_versions(org_id, product_families):
    device_info = {}
    seen_serials = set()
    
    try:
        # Fetch firmware upgrade information by device in the organization
        devices = dashboard.organizations.getOrganizationFirmwareUpgradesByDevice(org_id, upgradeStatuses='Completed')
        
        # Sort devices by timestamp in descending order to get the latest upgrades first, if timestamp missing then default to '' string
        devices.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Loop through devices to store current firmware shortName and model type, filtering by product family
        for device in devices:
            serial = device.get('serial', 'N/A')
            
            # Skip if we've already processed this serial. We do this because getOrganizationFirmwareUpgradesByDevice returns multiple entries per device serial.
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
def compare_firmware_versions(network_id, org_ids, product_families, desired_release_type):
    comparison_results = {}
    
    # Loop over each organization ID
    for org_id in org_ids:
        comparison_results[org_id] = {}
                
        # Get latest firmware available for product families
        latest_firmware_info = get_latest_firmware_info(network_id, product_families, desired_release_type)
            
        # Get current firmware running on devices, filtered by product families
        current_firmware_info = get_current_firmware_versions(org_id, product_families)
        
        # Compare the two and store results
        comparison_results[org_id][network_id] = {}
        
        for serial, device_info in current_firmware_info.items():
            # Ensure device_info is a dictionary (skip errors if any)
            if not isinstance(device_info, dict):
                continue

            product_family = device_info.get('product_family', 'unknown')
            
            # Get the latest firmware for the product family. Family is derived from the device's model prefix based on mapping defined above.
            latest_firmware = latest_firmware_info.get(product_family, {})
            latest_version = latest_firmware.get('latest_short_name', 'N/A')
            
            # Compare current firmware shortName (from the running version) with the latest version available
            comparison_results[org_id][network_id][serial] = {
                'hostname': device_info.get('hostname', 'N/A'),
                'ipAddress': device_info.get('ipAddress', 'N/A'),
                'model': device_info.get('model', 'N/A'),
                'running_firmware': device_info.get('running_firmware', 'N/A'),
                'latest_firmware': latest_version,
                'desired_release_type': latest_firmware.get('release_type', 'N/A'),
                'up_to_date': compare_versions(device_info.get('running_firmware', 'N/A'), latest_version) # Compare the running firmware with the latest shortName, return true if greater or equal.
            }
    
    # Output the results as JSON
    return json.dumps(comparison_results, indent=4)

# Call the function and print the comparison results for multiple org_ids
print(compare_firmware_versions(network_id, org_ids, product_families, desired_release_type))
