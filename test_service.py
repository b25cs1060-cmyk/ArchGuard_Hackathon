# test_service.py
import requests

API_KEY = "sk_live_51MxYz9876543210AbCdEf"

def fetch_data_from_remote():

    response = requests.get("http://slow-api-service.internal/data")
    return response.json()

def process_data(data):
    return eval(data)