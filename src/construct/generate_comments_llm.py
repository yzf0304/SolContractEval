import os
from openai import OpenAI
import json

client = OpenAI(
    api_key = os.environ.get("ALI_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

input_path = "../dataset/benchmark_third"
output_path = "../dataset/benchmark_comments"
if not os.path.exists(output_path):
    os.makedirs(output_path)

prompt_template = "Please write natspec-formatted comments for the entire contract of the following smart contract. The comments should include @notice and @dev. Clearly and concisely describe the functions of the contract. Write comments at the entire contract level. Also, empty the body content of each function in the contract, keeping only the function signature and {}. Do not add any text in {}. However, there is no need to do this for the constructor function and the receive function.\n"

sum = 0
for contract in os.listdir(input_path):
    if contract.endswith("json"):
        address = os.path.splitext(contract)[0]
        json_path = os.path.join(input_path, contract)
        sol_path = os.path.join(input_path, f"{address}_context.sol")
        output_file = os.path.join(output_path, address + ".txt")
        with open(json_path, "r") as f: data = json.load(f)
        with open(sol_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            line_count = len(lines)
            
        # if line_count > 600: continue
        # if data["code_blank"].count("{}") > 20 or data["code_blank"] == 0: continue

        print(address)
        print(data["code_blank"].count("{}"))
        if os.path.exists(output_file): continue

        sum += 1
        prompt = prompt_template + "```solidity\n" + data["code"] + "\n```"
        completion = client.chat.completions.create(
            model="qwen-max", 
            messages=[
                {'role': 'system', 'content': 'You are a Solidity smart contract development expert.'},
                {'role': 'user', 'content': prompt}],
            )
        response_message = completion.choices[0].message.content
        
        with open(output_file, "w") as f:
            f.write(response_message)

print(sum)