import requests
import time

url = "http://localhost:8502/_stcore/health"
print(f"Checking {url}...")
try:
    for i in range(10):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                print("Streamlit is UP!")
                break
        except:
            print(f"Attempt {i+1}: Down...")
            time.sleep(2)
except Exception as e:
    print(e)
