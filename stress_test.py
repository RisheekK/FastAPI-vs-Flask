import random
import string
import requests
import time
import json

FASTAPI_URL = "http://127.0.0.1:8000/contacts"
FLASK_URL = "http://127.0.0.1:5000/contacts"



# Number of concurrent requests
NUM_REQUESTS = 50

# Delay between requests (seconds)
DELAY = 0.1

payload_dict = {
    "username": "zxczxczxc",
    "phonenumber": 2222222222,
    "email": "asdadasd@jjk.com",
    "email_opt_in_status":True,
    "sms_opt_in_status":True,
    "state": "NJ",
    "country": "USA",
    "matm_owner": "TD00"
}

headers = {
    "Content-Type": "application/json",
    "Accept": "*/*",
    "Host": "127.0.0.1:8000",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive"
}

GET = "get"
POST = "post"

def update_payload(payload):
    payload["username"] =''.join(random.choices(string.ascii_letters, k=8))
    payload["phonenumber"] = random.randint(1000000000, 9999999999)
    payload["email"] = payload["username"] + "@test.com"
    return payload


def send_request(url):
    """
    Sends a GET request to the API endpoint and records processing time
    """
    time.sleep(DELAY)
    start_time = time.time()
    try:
        response = requests.get(url)
        # Check for successful response (optional)
        if response.status_code == 200:
            print(f"Request successful")
        else:
            print(f"Request failed: {response.status_code}")
        processing_time = time.time() - start_time
        print(f"Processing Time: {processing_time:.5f} seconds")
        return processing_time
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return 0  # Indicate error by returning 0 processing time

def post_request(url,payload):
    time.sleep(DELAY)
    start_time = time.time()
    try:
        response = requests.post(url=url, data= json.dumps(payload),headers=headers)
        # Check for successful response (optional)
        if response.status_code == 201:
            print(f"Request successful")
        else:
            print(f"Request failed: {response.status_code}")
        processing_time = time.time() - start_time
        print(f"Processing Time: {processing_time:.5f} seconds")
        return processing_time
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return 0  # Indicate error by returning 0 processing time


time_taken = []

def run_test(call_method,url):
    used_payload = []
    if call_method == "get":
        for i in range(NUM_REQUESTS):
            processing_time = send_request(url)
            time_taken.append(processing_time)
    if call_method == "post":
        for i in range(NUM_REQUESTS):
            payload = update_payload(payload_dict)
            used_payload.append(payload)
            processing_time = post_request(url,payload)
            time_taken.append(processing_time)

        print("intial payload requested")

        for payload in used_payload:
            payload["matm_owner"] = "TD01"
            processing_time = post_request(url,payload)
            time_taken.append(processing_time)

    return {"Method": call_method, "Url": url}

result = run_test(POST,FASTAPI_URL)

print(sum(time_taken))

f = open("test_result_2.txt", "a")
f.write(str(result) + str(sum(time_taken)) +"\n")
f.close()

# total_time = [sum(Seconds) for Seconds in time_taken]
# print(total_time)