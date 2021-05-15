from plyer import notification
import requests as r
from datetime import datetime
from datetime import date
import argparse
import json
import time
import re
import sys
import ssl

print("Vaccine slots availibility::")


DEBUG = False

def debug(data, name):
    if DEBUG:
        print(f"Data: {data}\nFunction name: {name}\n\n")


def error(err, err_type='normal'):
    if err_type == 'critical':
        print(f"Error: {err}")
        input('Press Any Key to EXIT...')
        sys.exit()
    else:
        print(f"Error: {err}")




def wizard():

    output = {'pincode': [], 'age': 18, 'date': date.today().strftime(
        '%d-%m-%Y'), 'state': '', 'district': '', 'interval': 300, 'validInfo': True}
    print('Please Answer the following questions. \nIf you don\'t know any, you can skip by pressing Enter, the default value will be used.\n')

    output['pincode'] = str(input(
        'Enter Single (OR Multiple) Pincodes(s) separated by space i.e. 380001 380002 (Skip if you wish to search by State and District):')).split(' ') or output['pincode']
    output['state'] = str(
        input("Enter the State (Skip if you're using Pincode):")) or output['state']
    output['district'] = str(
        input("Enter the District (Skip if you're using Pincode):")) or output['district']
    output['age'] = str(
        input('Enter Your Age i.e. 21 (Default = 18):')) or output['age']
    output['date'] = str(input(
        f"Enter Date in DD-MM-YYYY format i.e. 01-02-2021. \nIt is advised to use default date so press Enter(Default = {output['date']}):")) or output['date']
    output['interval'] = str(input(
        'Enter Interval in which to read Data from CoWin Website in Seconds (Default = 300):')) or output['interval']

    print()

    if(output['pincode'][0]=='' and (output['state']=='' and output['district']=='')):
        output['validInfo']=False
        error(
            'Neither Pincode, nor State with District entered. Exiting VaccineF. Please Try with Valid Inputs...')
        sys.exit()

    try:
        datetime.strptime(output['date'], '%d-%m-%Y')
    except Exception as e:
        error("Incorrect data format, should be DD-MM-YYYY OR Check the Input Date is Valid or not...")
        sys.exit()

    if not re.search(r"\d{2}\-\d{2}\-\d{4}", output['date']):
        error(f"Date {output['date']} is not in DD-MM-YYYY format", 'critical')

    return output


class vaccinator:

    def __init__(self, args):
        self.pincode = args['pincode']
        self.age = int(args['age'])
        self.date = args['date']
        self.state = args['state']
        self.district = args['district']

    def detect(self, data):
        output = {self.pincode: []}
        if 'error' in data.keys():
            error(data['error'])
            return output
        if data == {'centers': []} or data == {'sessions': []}:
            return output
        for center in data['centers']:
            for session in center['sessions']:
                if session['min_age_limit'] <= self.age and session['available_capacity'] > 0:
                    output[self.pincode].append([f"{center['name']}, {center['block_name']}, {center['district_name']}, {center['state_name']}, {center['pincode']}",
                                                   session['date'], session['slots']])
        debug(output, 'detect')
        return output

    def search_by_state(self):
        hdrs = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0"}
        did = state_id = 0
        res = district_data = ''
        states = {'andaman and nicobar islands': 1, 'andhra pradesh': 2, 'arunachal pradesh': 3, 'assam': 4, 'bihar': 5, 'chandigarh': 6, 'chhattisgarh': 7, 'dadra and nagar haveli': 8, 'daman and diu': 37, 'delhi': 9, 'goa': 10, 'gujarat': 11, 'haryana': 12, 'himachal pradesh': 13, 'jammu and kashmir': 14, 'jharkhand': 15, 'karnataka': 16,
            'kerala': 17, 'ladakh': 18, 'lakshadweep': 19, 'madhya pradesh': 20, 'maharashtra': 21, 'manipur': 22, 'meghalaya': 23, 'mizoram': 24, 'nagaland': 25, 'odisha': 26, 'puducherry': 27, 'punjab': 28, 'rajasthan': 29, 'sikkim': 30, 'tamil nadu': 31, 'telangana': 32, 'tripura': 33, 'uttar pradesh': 34, 'uttarakhand': 35, 'west bengal': 36}
        try:
            state_id = states[self.state.lower()]
        except KeyError:
            error('State not Found. Please enter any valid State...')
            sys.exit()
            return ''

        fetch_districts_url = f"https://cdn-api.co-vin.in/api/v2/admin/location/districts/{state_id}"
        try:
            res = r.get(fetch_districts_url, headers=hdrs)
        except Exception as e:
            error(f"Error while fetching district list\n{e}")
            return ''
        district_data = res.json()

        try:
            for district in district_data['districts']:
                if district['district_name'].lower() == self.district.lower():
                    did = district['district_id']
        except Exception as e:
            error(f"District not mentioned in Query. Please Try Again...")
            sys.exit()
            return ''

        if did == 0:
            error('District not Found. Please enter any valid District...')
            sys.exit()
            return ''
        statewise_url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id={did}&date={self.date}"
        try:
            res = r.get(statewise_url, headers=hdrs)
        except Exception as e:
            error(f"Error while fetching State-wise Data\n{e}")
            return ''

        if res.status_code != 200:
            error('Response Code Not OK!!')
            return ''
        try:
            debug(json.dumps(res.json(), indent = 1), 'search_by_state')
        except Exception as e:
            error('JSON Decode Error')
        else:
            return self.detect(res.json())
        return ''

    def search_by_pin(self):
        hdrs={'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:88.0) Gecko/20100101 Firefox/88.0"}
        url = f"https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByPin?pincode={self.pincode}&date={self.date}"
        try:
            res = r.get(url, headers=hdrs)
        except Exception as e:
            error(e)
        else:
            if res.status_code != 200:
                error('Response Code Not OK !!')
                return ''
            try:
                debug(json.dumps(res.json(), indent = 1), 'search_by_pin')
            except Exception as e:
                error('JSON Decoder Error')
            else:
                return self.detect(res.json())
        return ''
  
def desktop_notification(data):
    notification.notify(
    	app_name = "VaccineF",
        title = 'VaccineF Found Slots!',
        message = data,
        timeout = 12
        )


def repeater(args):
    location_type = ''
    data = {}
    messages = ''
    run = vaccinator(args)
    if args['state']:
        location_type = f"State: {args['state']}, District: {args['district']}" 
        data = run.search_by_state()
    if args['pincode']:
        location_type = f"Pincode: {args['pincode']}"
        data = run.search_by_pin()

    if data == {args['pincode']:[]} or not data:
        print(f"No Slots available for {location_type}")
        return ''
    sequence = 1
    for i in data[args['pincode']]:
        messages += f"\n{sequence}. Date: {i[1]}\n   Location: {i[0]}\n   Slots: {i[2]}"
        sequence += 1
    messages = f"***Available at {location_type}***{messages}"
    return messages

def main():

    all_args = wizard() 

    if('validInfo' in all_args and not all_args['validInfo']):
        sys.exit(0)
    debug(all_args, 'main')
    
    counter = 1
    pins = all_args['pincode']

    while True:
        print(f"\n[Time: {datetime.now().strftime('%H:%M:%S')}]  Try: [{counter}]")
        found = ''
        if pins:
            for pin in pins :
                all_args['pincode'] = pin 
                found += repeater(all_args)
        else:
            found += repeater(all_args)

        if found:
            print(found)
            print('\nInfo: Slots have been found. Exit the Terminal to stop the Beeping Sound')
            desktop_notification(f"Slots are available for your mentioned Query. \nCheck your Terminal for Detailed Information.")
            for _ in range(1,int(all_args['interval'])):
                sys.stdout.write('\a')
                sys.stdout.flush()
                time.sleep(1)

        else:
            print(f"Info: Script will be Sleeping for {int(all_args['interval'])/60} minutes until the Next Try. Please Wait...")
            time.sleep(int(all_args['interval']))
        counter += 1
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\n\nUser Aborted the Program.\nExiting, Please Wait...')
        sys.exit()
