import os
import sys
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()

APP_SECRET = os.environ.get("APP_SECRET", "")
BASE_URL = "http://localhost:8001/api/provider"

def make_request(method, path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {
        "X-App-Secret": APP_SECRET,
        "Content-Type": "application/json"
    }
    
    if data is not None:
        data_bytes = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)
        
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        if e.code == 404 and "/active-job" in path:
            return None
        print(f"\n[HTTP Error {e.code}] {url}")
        try:
            print(f"Details: {json.loads(error_body)}")
        except:
            print(f"Details: {error_body}")
        return None
    except Exception as e:
        print(f"\n[Error] Failed to connect to API: {e}")
        return None

def login():
    print("=== Provider App Simulator ===")
    phone = input("Enter your provider phone number (e.g., 923000000101): ").strip()
    
    data = {"phone": phone}
    result = make_request("POST", "/login", data)
    
    if result:
        print(f"\n✅ Logged in as: {result['name']} (ID: {result['id']})")
        return result
    return None

def get_active_job(provider_id):
    return make_request("GET", f"/{provider_id}/active-job")

def main():
    if not APP_SECRET:
        print("Error: APP_SECRET not found in .env file.")
        sys.exit(1)
        
    provider = login()
    if not provider:
        sys.exit(1)
        
    provider_id = provider["id"]
    
    while True:
        input("\nPress Enter to check for active jobs...")
        job = get_active_job(provider_id)
        
        if not job:
            print("No active jobs found. Keep waiting.")
            continue
            
        print("\n" + "="*40)
        print("📱 ACTIVE JOB FOUND")
        print("="*40)
        print(f"Booking ID:   {job['booking_id']}")
        print(f"Status:       {job['status']}")
        print(f"Customer:     {job['customer_name']} ({job['customer_phone']})")
        print(f"Issue:        {job['issue']}")
        print(f"Service Area: {job['customer_city'] or 'Unknown'}")
        print("="*40)
        
        status = job['status']
        
        print("\nActions Available:")
        if status == "pending":
            print("1. Accept Job (Provide Estimate)")
            print("9. Cancel Job")
            choice = input("Select action: ").strip()
            if choice == "1":
                while True:
                    try:
                        min_cost = int(input("Enter Estimated Cost Min (PKR): ").strip())
                        max_cost = int(input("Enter Estimated Cost Max (PKR): ").strip())
                        break
                    except ValueError:
                        print("Invalid input. Please enter numeric values only (e.g. 2000).")
                make_request("POST", f"/bookings/{job['booking_id']}/accept", {
                    "estimated_cost_min": min_cost,
                    "estimated_cost_max": max_cost
                })
            elif choice == "9":
                make_request("POST", f"/bookings/{job['booking_id']}/cancel", {"cancelled_by": "provider"})
                
        elif status == "accepted":
            print("1. Confirm / Start Job")
            print("9. Cancel Job")
            choice = input("Select action: ").strip()
            if choice == "1":
                make_request("POST", f"/bookings/{job['booking_id']}/confirm")
            elif choice == "9":
                make_request("POST", f"/bookings/{job['booking_id']}/cancel", {"cancelled_by": "provider"})
                
        elif status == "confirmed":
            print("1. I'm On My Way (En Route)")
            choice = input("Select action: ").strip()
            if choice == "1":
                make_request("POST", f"/bookings/{job['booking_id']}/status", {"status": "en_route"})
                
        elif status == "en_route":
            print("1. I've Arrived")
            choice = input("Select action: ").strip()
            if choice == "1":
                make_request("POST", f"/bookings/{job['booking_id']}/status", {"status": "arrived"})
                
        elif status == "arrived":
            print("1. Mark Job Complete (Finalize Bill)")
            choice = input("Select action: ").strip()
            if choice == "1":
                while True:
                    try:
                        final_cost = int(input("Enter Final Cost (PKR): ").strip())
                        break
                    except ValueError:
                        print("Invalid input. Please enter numeric values only (e.g. 2000).")
                make_request("POST", f"/bookings/{job['booking_id']}/complete", {"final_cost": final_cost})
                print("\n✅ Job completed successfully!")
                
        else:
            print(f"Unhandled status: {status}")

if __name__ == "__main__":
    main()
