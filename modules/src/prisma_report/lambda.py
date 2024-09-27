import requests
import json
import pandas as pd
from datetime import datetime
from csv import QUOTE_NONNUMERIC
from io import StringIO
import urllib.parse
import boto3
import calendar
import time
import traceback
URL = "https://api.eu.prismacloud.io/login"
INVENTORY_URL = "https://api.eu.prismacloud.io/v3/inventory?cloud.type=aws&groupBy=cloud.service"
# ALERT_URL = "https://api.eu.prismacloud.io/report/90943a0a-82a7-4b3c-a5a6-5e0fca16f74e/download" every monday
ALERT_URL = "https://api.eu.prismacloud.io/report/4c761c2e-9fc4-4ee4-a3fa-95ed4f97c392/download"
PASSWORD = "ZtO8gLrExIOVdq/47i/u7tmP1jE="
PRISMA_ID = "5560034072019170434"
USERNAME = "73ceba60-2844-4311-ac4d-1adccccf1482"
TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
S3_BUCKET_NAME = "prisma-aws-reporting-logs"
INV_OUT_FILE = 'Inventory_Report.csv'
INV_RES_TYPE_OUT_FILE = 'Inventory_Resource_Type_Report.csv'
ALT_OUT_FILE = "Alert_Report.csv"
s3_client = boto3.client('s3')
result_list = []
current_date = datetime.now()
year = str(current_date.year)
month = calendar.month_name[current_date.month]
day = current_date.day
date_folder = f"{year}/{month}/{day}-{month}-{year}/"
alert_timestamp, alert_req_timestamp = None, None

# Login to Prisma Cloud using the retrieved credentials


def prismacloud_login(url, password, prisma_id, username):
    """
    This function attempts to login to Prisma Cloud using the retrieved credentials.
    Raises:
        SystemExit: If login fails or unexpected data is received during the process.
    """
    # Create the payload dictionary with actual values
    payload = {
        "password": password,
        "prismaId": prisma_id,
        "username": username
    }
    # Convert the payload dictionary to a JSON string
    payload_json = json.dumps(payload)

    # Set the headers for the POST request
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Accept': 'application/json; charset=UTF-8'
    }

    # Send the POST request with the updated payload
    response = requests.post(url, headers=headers, data=payload_json)

    # Check the response
    if response.status_code == 200:
        print("Login successful!")
        # Additional handling for successful login
    else:
        print(f"Login failed with status code: {response.status_code}")
        print(response.text)  # Print the response text for debugging purpos
        # print(json.dumps(response.json(), indent=4))
        # load token into a variable from above response
    token_variable = response.json()['token']
    return token_variable


TOKEN_VARIABLE = prismacloud_login(URL, PASSWORD, PRISMA_ID, USERNAME)
# Get API response
def get_api_response(api_url):
    """
    This function sends a GET request to the specified URL and returns the API response.
    Args:
        url (str): The URL to send the GET request to.
        token_variable (str): The token to include in the request headers.
    Returns:
        dict: The API response as a dictionary.
    """
    # Set the headers for the GET request
    headers = {
        'Accept': 'application/json; charset=UTF-8',
        'x-redlock-auth': TOKEN_VARIABLE
    }
    payload = {}
    # Send the GET request
    response = requests.request(
        "GET", url=api_url, headers=headers, data=payload)

    # Check the response status code
    if response.status_code == 200:
        # Parse the JSON response
        # api_response = json.dumps(response.json(), indent=4)
        # api_response_data = json.loads(api_response)
        return response
    else:
        print(
            f"Error: API request failed with status code {response.status_code}")
        return None

def perform_request_with_backoff(method, url, headers, data=None, retries=5, backoff_factor=1):
    """Perform HTTP request with exponential backoff.

    Args:
    method: HTTP method as a string, 'GET' or 'POST'.
    url: URL for the request.
    headers: Dictionary of request headers.
    data: Dictionary of POST data for POST requests. Defaults to None.
    retries: Maximum number of retries. Defaults to 5.
    backoff_factor: Multiplier for how long to wait between retries. Defaults to 1.

    Returns:
    A requests.Response object.
    """
    for attempt in range(retries):
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers, timeout=10)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if response.status_code != 429:  # If not rate-limited,
            return response

        # If we are rate-limited (HTTP 429),
        sleep_time = backoff_factor * (2 ** attempt)
        print(f"Rate limited. Retrying in {sleep_time} seconds.")
        time.sleep(sleep_time)

    # After all retries, return the last response (which might be a 429).
    return response

# generate inventory resource type url
def generate_inventory_resource_type_url(cloud_type, cloud_service, group_by):
    try:
        # Encode the cloud_service parameter to handle spaces
        encoded_cloud_service = urllib.parse.quote(cloud_service)
        # Construct the URL with encoded parameters
        url = f"https://api.eu.prismacloud.io/v3/inventory"
        url = f"{url}?cloud.type={cloud_type}&cloud.service={encoded_cloud_service}&groupBy={group_by}"
        return url
    except Exception as e:
        print(f"Error while generating inventory resource type url: {e}")

# add timestamp and requestedTimestamp columns to the reports
def add_timestamp_column(result):
    try:
        timestamp = result['timestamp']
        req_timestamp = result['requestedTimestamp']
        # Convert the inventory timestamp to the desired format (defined in TIME_FORMAT)
        timestamp = datetime.fromtimestamp(
            timestamp / 1000).strftime(TIME_FORMAT)
        req_timestamp = datetime.fromtimestamp(
            req_timestamp / 1000).strftime(TIME_FORMAT)
        return timestamp, req_timestamp
    except Exception as e:
        print(f"Error while adding timestamp column: {e}")

# Genearate Inventory Report
def get_inventory_report(inventory_url):
    try:
        inventory_response = get_api_response(inventory_url)
        inventory_result = json.dumps(inventory_response.json(), indent=4)
        inventory_data = json.loads(inventory_result)
        inventory_summary = inventory_data['summary']
        inventory_df = pd.DataFrame(inventory_data['groupedAggregates'])
        timestamp, req_timestamp = add_timestamp_column(inventory_data)
        alert_timestamp, alert_req_timestamp = timestamp, req_timestamp
        # add timestamp and requestedTimestamp columns to the dataframe
        inventory_df['timestamp'] = timestamp
        inventory_df['requestedTimestamp'] = req_timestamp
        inventory_df['transaction_date'] = current_date.strftime('%Y-%m-%d')
        inventory_df = inventory_df.fillna(0)
        return inventory_df, alert_timestamp, alert_req_timestamp

    except Exception as e:
        print(f"Error while generating inventory report: {e}")

# Generate Inventory Resource Type Report
def get_inventory_resource_type_report(inventory_resource_type_url, resource_identity):
    try:
        inventory_resource_type_response = get_api_response(
            inventory_resource_type_url)
        inventory_resource_type_result = json.dumps(
            inventory_resource_type_response.json(), indent=4)
        inventory_resource_type_data = json.loads(
            inventory_resource_type_result)
        # Create a pandas DataFrame from the 'groupedAggregates' list
        inventory_resource_type_df = pd.DataFrame(
            inventory_resource_type_data['groupedAggregates'])
        timestamp, req_timestamp = add_timestamp_column(
            inventory_resource_type_data)
        # add timestamp and requestedTimestamp columns to the dataframe
        inventory_resource_type_df['timestamp'] = timestamp
        inventory_resource_type_df['requestedTimestamp'] = req_timestamp
        inventory_resource_type_df['resourceIdentity'] = resource_identity
        inventory_resource_type_df['transaction_date'] = current_date.strftime(
            '%Y-%m-%d')
        return inventory_resource_type_df

    except Exception as e:
        print(f"Error while generating resource type report: {e}")

# Generate Alert Report based on Month
def get_alert_report(alert_url, alert_timestamp, alert_req_timestamp):
    try:
        # Data structure for CSV
        jsonTable = []
         # Initialize response2 as an empty dictionary
        response2 = {}
        # I must first capture all policies that are linked to active alerts
        url1 = "https://api.eu.prismacloud.io/alert/v1/policy"
        # Get today's datetime
        today = datetime.now().date()
        # Get the first day of the current month
        first_day_of_month = today.replace(day=1)
        # Get the end of today
        end_of_today = datetime.combine(today, datetime.max.time())
        # Convert datetime to timestamp UNIX in seconds and then to milliseconds
        start_time = int(time.mktime(first_day_of_month.timetuple()) * 1000)
        end_time = int(time.mktime(end_of_today.timetuple()) * 1000)
        payload1 = json.dumps(
            {
            "filters": [
                {"name": "alert.status", "operator": "=", "value": "open"},
                {"name": "timeRange.type", "operator": "=", "value": "ALERT_OPENED"},
                {"name": "policy.severity", "operator": "=", "value": "critical"},
                {"name": "policy.severity", "operator": "=", "value": "high"},
                {"name": "policy.severity", "operator": "=", "value": "medium"},
                {"name": "policy.severity", "operator": "=", "value": "low"},  
                {"name": "policy.severity", "operator": "=", "value": "informational"},
            ],
            "timeRange": {
                "type": "absolute",
                "value": {
                    "endTime": end_time,
                    "startTime": start_time
                }
                },
            "sortBy": [
                "severity:desc",
                "alertCount:desc"
            ]
        }
        )
        headers1 = {  
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'x-redlock-auth': TOKEN_VARIABLE
        }
        response1 = json.loads(requests.request("POST", url1, headers=headers1, data=payload1).text)
        url2 = "https://api.eu.prismacloud.io/v2/alert"
        #Filter the data that i need and create new array with the field i need
        for policy in response1["policies"]:          
            #peek single policy
            policyID = policy["policyId"]          
            #get all cloud account for policy violation and count how many violtion
            accounts = {}          
            #prepare loadbalance rotation
            table = []
            pageToken = ""        
            while(True):
                time.sleep(1)
                payload2 = json.dumps(
                    {
                    "detailed": "false",
                    "limit": 100,
                    "pageToken": pageToken,
                    "filters": [
                        {"name": "policy.id", "operator": "=", "value": policyID},
                        {"name": "alert.status", "operator": "=", "value": "open"},
                        {"name": "timeRange.type", "operator": "=", "value": "ALERT_OPENED"},
                        {"name": "policy.severity", "operator": "=", "value": "critical"},
                        {"name": "policy.severity", "operator": "=", "value": "high"},
                        {"name": "policy.severity", "operator": "=", "value": "medium"},
                        {"name": "policy.severity", "operator": "=", "value": "low"},  
                        {"name": "policy.severity", "operator": "=", "value": "informational"}
                    ],
                    "timeRange": {
                    "type": "absolute",
                    "value": {
                        "endTime": end_time,
                        "startTime": start_time
                    }
                    },
                }
                )          
                headers2 = {  
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'x-redlock-auth': TOKEN_VARIABLE
                }
                #responseClear = requests.request("POST", url2, headers=headers2, data=payload2).text
                #response2 = json.loads(responseClear)
                responseClear = requests.request("POST", url2, headers=headers2, data=payload2)
                if responseClear.status_code == 200:
                    try:
                        response2 = json.loads(responseClear.text)
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
                        # Handle the error (log it, return an empty dict, etc.)
                else:
                    print(f"Request failed with status code {responseClear.status_code}")
                #exit condition 1 (if there is no more element, just a check to dont throw exception
                if 'items' in response2:
                    table = table + response2['items']
                else:            
                    break
               
                #exit condition 2 (if this is last API call)
                if(len(response2['items']) != 100):
                    break              
                pageToken = response2["nextPageToken"]  
                                 
            for alert in table:
                    name = alert['resource']['account']
                    id = alert['resource']['accountId']
                    cloudtype = alert['resource']['cloudType']
                    group = alert['resource']['cloudAccountGroups'][0]
                    if name not in accounts.keys():
                        accounts[name] = {
                                "name" : name,
                                "id" : id,
                                "cloudType" : cloudtype,
                                "group" : group,
                                "count" : 1
                            }
                    else:
                        accounts[name]["count"] = int(accounts[name]["count"]) + 1              
            for account in accounts.values():
                    jsonTable.append(
                        {
                            "Policy Name" : policy["policyName"],
                            "Policy Type" : policy["policyType"],
                            "Policy Severity" : policy["severity"].upper(),
                            "Cloud Type" : account["cloudType"].upper(),
                            "Cloud Account Name" : account["name"],
                            "Cloud Account Id" : account["id"],
                            "Cloud Account Group" : account["group"],
                            "Status" : "fail",
                            "Failed Resource Count" : account["count"]
                        }
                    )
        # Return an empty DataFrame if jsonTable is empty
        if not jsonTable:
            return pd.DataFrame()
        # convert jsonTable to dataframe
        alert_df = pd.DataFrame(jsonTable)
        alert_df = alert_df.fillna(0)
        # Add the timestamp and requestedTimestamp columns to the DataFrame
        alert_df['timestamp'] = alert_timestamp
        alert_df['requestedTimestamp'] = alert_req_timestamp
        alert_df['transaction_date'] = current_date.strftime('%Y-%m-%d')  
        return alert_df

    except Exception as e:
        # Utilize traceback to print the exception message and the line number
        traceback_details = traceback.format_exc()
        print(f"An unexpected error occurred while generating Alert Report: {e}\nTraceback details: {traceback_details}")
        # You might want to return or handle the exception in some way after logging it
        return {
            'statusCode': 500,
            'body': json.dumps(f'An unexpected error occurred while generating Alert Report. Error details have been logged.')
        }

# Function to upload report to S3


def upload_report_to_s3(report_df, file_name):
    #print('---1-----')
    # print(report_df)
    csv_buffer = report_df.to_csv(index=False, quoting=QUOTE_NONNUMERIC)
    file_path = '/tmp/' + file_name
    with open(file_path, 'w') as f:
        f.write(csv_buffer)
    s3_key = f"{date_folder}{file_name}"
    s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)
    return s3_key


def handler(event, context):
    alert_key, inventory_key = None, None
    try:
        # get Alert report
        inventory_report, alert_timestamp, alert_req_timestamp = get_inventory_report(
            INVENTORY_URL)
        # alert_response = get_alert_report(ALERT_URL,alert_timestamp, alert_req_timestamp)
        # get serviceName column value from the dataframe
        inventory_servicename = inventory_report['serviceName']
        for i in inventory_servicename:
            # if i == 'Amazon EC2' or i == 'Amazon RDS':
            inventory_resource_type_url = generate_inventory_resource_type_url(
                'aws', i, 'resource.type')
            result = get_inventory_resource_type_report(
                inventory_resource_type_url, i)
            result_list.append(result)

        combined_df = pd.concat(result_list, ignore_index=True)
        # replace all NaN value with 0 value
        inventory_resource_type_report = combined_df.fillna(0)

        # Upload reports to S3
        inventory_key = upload_report_to_s3(inventory_report, INV_OUT_FILE)
        inventory_resource_type_key = upload_report_to_s3(
            inventory_resource_type_report, INV_RES_TYPE_OUT_FILE)
        # alert_key = upload_report_to_s3(alert_response,ALT_OUT_FILE)
        alert_response = get_alert_report(ALERT_URL, alert_timestamp, alert_req_timestamp)
        if isinstance(alert_response, pd.DataFrame):
            # Proceed to upload
            alert_key = upload_report_to_s3(alert_response, ALT_OUT_FILE)
        else:
            # Handle error or unexpected return type
            raise Exception(f"Expected DataFrame, got {type(alert_response)}")
        # Return success response if all S3 uploads are successful
        status_code = 200
        body = 'All S3 uploads completed successfully.'
        # Print status code and body
        print("Status Code:", status_code)
        print("Body:", body)
        # Return response
        return {
            'statusCode': status_code,
            'body': json.dumps(body)
        }

    except Exception as e:
        # If any error occurs during the upload process, perform rollback
        print(f"An error occurred: {e}")
        s3_key = f"{date_folder}{ALT_OUT_FILE}"
        if alert_key is None:
            alert_key = s3_key
        rollback(inventory_key, inventory_resource_type_key, alert_key)
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error occurred: {e}. Rollback initiated.')
        }


def rollback(*s3_keys):
    # Delete uploaded objects from S3
    for s3_key in s3_keys:
        try:
            s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
            print(f"Deleted object from S3: {s3_key}")
        except Exception as e:
            print(f"Error occurred while deleting object from S3: {e}")
