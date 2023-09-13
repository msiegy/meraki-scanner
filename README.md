# meraki-scanner
Simple Proof of Concept exploring the available Meraki Dashboard APIs at https://developer.cisco.com/meraki/api/overview/ to pull down software versions and other information for the purpose of vulnerability management.

#### Demo
   Configure ENV values for your Meraki dashboard and run python main.py
   <br>The script will pull down firmware data for every device in the organization provided. Then all Meraki vulnerabilities, regardless of exposure are pulled down using Cisco's OpenVuln API.
    
   <img src=gifs/scannerdemo.gif width="100%" height="100%">
