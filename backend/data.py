import requests

url = "https://api.coursetable.com/api/catalog/public/202601"

response = requests.get(url)
response.raise_for_status()   # throws if request failed

data = response.json()        # parsed JSON → Python dict / list


d = data[500]
# pretty pring d
import json
print(json.dumps(d, indent=4))

print(len(data))
for i in data:
    try:
        print(i["subject"])
    except:
        pass