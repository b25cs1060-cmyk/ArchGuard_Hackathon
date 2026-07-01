import requests
from flask import Flask, request

app = Flask(__name__)

# ANTI-PATTERN 1: Hardcoded credentials in source code
AWS_SECRET_KEY = "AKIAIOSFODNN7EXAMPLE"

@app.route('/checkout')
def process_checkout():
    try:
        # ANTI-PATTERN 2: External HTTP call with NO timeout parameter.
        # If the external payment service hangs, this will exhaust server threads (Blast Radius: High).
        # ANTI-PATTERN 3: No retry logic or circuit breaker wrapped around this call.
        payment_response = requests.post(
            "https://api.unreliable-payment-gateway.com/charge",
            headers={"Authorization": f"Bearer {AWS_SECRET_KEY}"}
        )
        
        return {"status": "success", "receipt": payment_response.json()}
    
    # ANTI-PATTERN 4: Catch-all bare exception. Masks critical failures and makes debugging impossible.
    except Exception:
        print("Something went wrong during payment.")
        return {"status": "error", "message": "Failed"}

# ANTI-PATTERN 5: Missing /health or /ping endpoint. 
# Load balancers will not know if this service is actually alive or dead.

if __name__ == '__main__':
    # ANTI-PATTERN 6: Running the development server in a production-like environment with debug=True
    app.run(host='0.0.0.0', port=8000, debug=True)