""" Copyright (c) 2020 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
           https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied. 
"""

import requests, os, math
import json
from dotenv import load_dotenv
import base64
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from meraki import DashboardAPI

#Create FloorPlans and save their ids generated by Meraki
def create_floorplans(floorplans, network, latitude, longitude):
    for i in floorplans:
        drawing = svg2rlg('floorplan/image-' + i["imageId"])
        renderPM.drawToFile(drawing, f"floorplan/image-{i['imageId']}.png", fmt='PNG')

        with open("floorplan/image-"+i["imageId"]+".png", "rb") as img_file:
            b64_string = base64.b64encode(img_file.read())
        imgstring= b64_string.decode('utf-8')

        headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Cisco-Meraki-API-Key": os.environ['MERAKI_API_KEY']
            }

        url = "https://api.meraki.com/api/v1/networks/"+ network + "/floorPlans"

        print('NAME: ' + i["name"].replace('ü', 'u')[:25])
        payload = {
                "center": {
                        "lat": float(latitude.split(" ")[1]),
                        "lng": float(longitude.split(" ")[1])
                        },
                "name": i["name"].replace('ü', 'u')[:25],
                "imageContents": imgstring
        }
        response = requests.request('POST', url, headers=headers, json = payload).json()
        print(response)
        i["floorPlanId-Meraki"]=response['floorPlanId']
        width = abs(response['bottomRightCorner']['lng'] - response['bottomLeftCorner']['lng'])
        height = abs(response['topRightCorner']['lat'] - response['bottomRightCorner']['lat'])
        i['width-Meraki'] = width
        i['height-Meraki'] = height
        i['bottomLeft-Meraki'] = response['bottomLeftCorner']
    place_devices_on_fp(floorplans, network)

#Read accessPoints.json to place the APs/devices on the floorplans       
def place_devices_on_fp(floorplans, network):
    floorplans=floorplans
    ap_file = open('floorplan/accessPoints.json')
    data = json.load(ap_file)
    m = DashboardAPI(os.environ['MERAKI_API_KEY'])
    for ap in data['accessPoints']:
        for fp in floorplans:
            if ap["location"]["floorPlanId"] == fp["id"]:
                for device in m.networks.getNetworkDevices(network):
                    print(device)
                    print(ap['name'])
                    if "MR" in device['model'] and device["mac"] == ap['name']:
                        url = "https://api.meraki.com/api/v1/devices/"+device["serial"] 
                        headers = {
                            "Content-Type": "application/json",
                            "Accept": "application/json",
                            "X-Cisco-Meraki-API-Key": os.environ['MERAKI_API_KEY']
                        }
                        device['lng'] = fp['bottomLeft-Meraki']['lng'] + (ap["location"]["coord"]["x"]/fp['width'])*fp['width-Meraki']
                        device['lat'] = fp['bottomLeft-Meraki']['lat'] + (ap["location"]["coord"]["y"]/fp['height'])*fp['height-Meraki']
                        device['floorPlanId'] = fp["floorPlanId-Meraki"]
                        response = requests.request('PUT', url, headers=headers, json=device)
                        print(response.text)
    ap_file.close()

    
if __name__ == "__main__":
    load_dotenv()
    create_floorplans()

