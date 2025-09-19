import os
import json

contracts = []
with open("document/contracts.json", "r", encoding='utf-8') as f:
    for line in f:
        data = json.loads(line.strip())
        contracts.append(data)

filtered_contracts = [x for x in contracts if x['txcount'] > 1000]
filtered_contracts.sort(key=lambda x: x['txcount'], reverse=True)

output_data = filtered_contracts[:8000] 
with open("document/top_8000.json", "w") as f:
    json.dump(output_data, f, indent=4)

print(f"len(output_data)")