import requests
import json
import urllib.request,urllib.error
from bs4 import BeautifulSoup
import os

proxies = {
    'https': 'https://127.0.0.1:10808',     
    'http': 'http://127.0.0.1:10808',       
}
head = { 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
}
# opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
# urllib.request.install_opener(opener)

def get_balance(address, api_key):
    url = f'https://api.etherscan.io/api?module=account&action=balance&address={address}&tag=latest&apikey={api_key}'
    # url = f'https://api.etherscan.io/api'
    print(url)
    params = {
        'module': 'account',
        'action': 'balance',
        'address': address,
        'tag': 'latest',
        'apikey': api_key
    }
    # response = requests.get(url, headers=head)
    request = urllib.request.Request(url, headers=head, method="GET")
    response = urllib.request.urlopen(request, timeout=30)
    print(response)
    data = response.json()
    if data['status'] == '1':
        balance = data['result']
        # 将 wei 转换为 ETH
        balance_eth = float(balance) / 1e18
        return balance_eth

def get_transactions(address, api_key, startblock=0, endblock=99999999, sort='asc'):
    url = "https://etherscan.io/address/" + address
    response = requests.get(url, headers=head, timeout=20)
    html_content = response.text
    print(url)
    with open("html.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    soup = BeautifulSoup(html_content, 'html.parser')
    a_tag = soup.find('a', href=lambda x: x and '/txs?a=' in x, attrs={'data-bs-toggle': 'tooltip'})

    if a_tag:
        number = a_tag.text.strip()
        print(number)
        return number
    else: return None

api_key = os.environ.get("ETHERSCAN_API_KEY")
with open("top_5000.json", "r") as f:
    data = json.load(f)
contracts = []
with open("new_tx.json", "r") as f:
    for line in f:
        line_data = json.loads(line.strip())
        contracts.append(line_data)

new_contracts = []
for contract in data:
    address = contract["address"]
    print(address)

    for tx in contracts:
        if address == tx["address"]: 
            tmp = tx
            balance = get_balance(address, api_key)
            if balance: tmp["balance"] = balance
            new_contracts.append(tmp)
            break

    
new_contracts.sort(key=lambda x:x['txcount'], reverse=True)
with open("top_1000.json", "w") as f:
    json.dump(new_contracts[0:10], f, indent=4)