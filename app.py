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

from email import header
from flask import Flask, render_template, request
from dotenv import load_dotenv
from meraki import DashboardAPI
import zipfile, json, os
import floorplans as fp
import requests

app = Flask(__name__)

FLOORPLAN_FILENAME = "floorplan"
SUFFIX = 'com'

#Read data from json file
def getJson(filepath):
	with open(filepath, 'r') as f:
		json_content = json.loads(f.read())
		f.close()

	return json_content

#Write data to json file
def writeJson(filepath, data):
    with open(filepath, "w") as f:
        json.dump(data, f)
    f.close()

@app.route('/', methods=["GET", "POST"])
def index():
    global SUFFIX
    selected_org=None
    selected_network=None
    # Floorplan upload
    if request.method == "POST":
        selected_org=request.form.get('organizations_select')
        selected_network=request.form.get('network')
        latitude=request.form.get('latitude')
        longitude=request.form.get('longitude')

        # Download floorplan ESX file
        uploaded_file = request.files
        file_dict = uploaded_file.to_dict()
        the_file = file_dict["floorplan"]
        if not the_file.filename.lower().endswith('.esx'):
            return "Please upload a valid ESX format, or enter the API keys manually"
        with open(f"{FLOORPLAN_FILENAME}.esx", 'wb') as f:
            f.write(the_file.read())

        # Load & Unzip the Ekahau Project File
        with zipfile.ZipFile(f"{FLOORPLAN_FILENAME}.esx", 'r') as myzip:
            myzip.extractall(FLOORPLAN_FILENAME)

        floorplans = None
        with open(f"{FLOORPLAN_FILENAME}/floorPlans.json", 'r') as f:
            floorplans = json.load(f)['floorPlans']
        
        try:
            fp.create_floorplans(floorplans, selected_network, latitude, longitude, SUFFIX)
            return render_template('home.html', hiddenLinks=True, dropdown_content=get_orgs_and_networks(), selected_elements={'organization':selected_org, 'networkid':selected_network}, success=True)
        except Exception as e:
            print("This is the exception: " + str(e))
            return render_template('home.html', hiddenLinks=True, dropdown_content=get_orgs_and_networks(), selected_elements={'organization':selected_org, 'networkid':selected_network}, error=True)

    return render_template('home.html', hiddenLinks=True, dropdown_content=get_orgs_and_networks(), selected_elements={'organization':selected_org, 'networkid':selected_network})

def get_orgs_and_networks():
    global SUFFIX
    apikey = os.environ['MERAKI_API_KEY']
    m = DashboardAPI(apikey, base_url='https://api.meraki.com/api/v1')
    try:
        m.organizations.getOrganizations()
    except:
        SUFFIX = 'cn'
        m = DashboardAPI(apikey, base_url='https://api.meraki.cn/api/v1')
    result = []
    for org in m.organizations.getOrganizations():
        org_entry = {
            "orgaid" : org['id'],
            "organame" : org['name'],
            "networks" : []
        }
        try:
            for network in m.organizations.getOrganizationNetworks(org['id']):
                org_entry['networks'] += [{ 
                    'networkid' : network['id'],
                    'networkname' : network['name']
                }]
            result += [org_entry]
        except:
            print('Broken org: ' + org['name'])
    return result

if __name__ == '__main__':
    load_dotenv()
    app.run(port=5004,debug=True)
    