# meraki-scanner
Simple Proof of Concept exploring the available Meraki Dashboard APIs at https://developer.cisco.com/meraki/api/overview/ to pull down software versions and other information for the purpose of vulnerability management.

#### compare_firmware.py Example Output
This script will pull inventory data and current running versions and compare against the latest available versions of the desired release type.
```
{
    "L_3xxxxxxxx": {
        "ABAB-ABAB-ABAB": {
            "hostname": "MS225-IDF",
            "ipAddress": "192.168.1.26",
            "model": "MS225-24P",
            "running_firmware": "MS 16.7",
            "running_release_type": "N/A",
            "latest_firmware": "MS 17.1.2",
            "desired_release_type": "candidate",
            "up_to_date": false
        },
        "CDCD-CDCD-CDCD": {
            "hostname": "MS130-8P",
            "ipAddress": "192.168.1.144",
            "model": "MS130-8P",
            "running_firmware": "MS 17.1.2",
            "running_release_type": "N/A",
            "latest_firmware": "MS 17.1.2",
            "desired_release_type": "candidate",
            "up_to_date": true
        },
        "XYXY-XYXY-XYXY": {
            "hostname": "MS390-48P",
            "ipAddress": "192.168.1.149",
            "model": "C9300-48P",
            "running_firmware": "CS 15.21.1",
            "running_release_type": "N/A",
            "latest_firmware": "CS 17.1.3",
            "desired_release_type": "candidate",
            "up_to_date": false
        }
    }
}
```



#### Main.py Demo
   Configure ENV values for your Meraki dashboard and run python main.py
   <br>The script will pull down firmware data for every device in the organization provided. Then all Meraki vulnerabilities, regardless of exposure are pulled down using Cisco's OpenVuln API.
    
   <img src=gifs/scannerdemo.gif width="100%" height="100%">
