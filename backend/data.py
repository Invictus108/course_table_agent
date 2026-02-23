import json

# load json
with open('202601.json', 'r', encoding="utf-8") as f:
    data = json.load(f)

s = set()
for i in data["data"]["courses"]:
    for j in i["listings"]:
        s.add(j["subject"])

print(s)


