import os
from openai import OpenAI, BadRequestError
import json
import requests
import time

models = [
    "gpt-4o",
    "o4-mini",
    "qwen2.5-coder-32b-instruct",
    "gemini-2.0-flash-exp",
    "claude-3-7-sonnet-20250219",
    "deepseek-reasoner",
    "deepseek-r1"
]
print(str(models))
model_num = int(input("Enter model index: "))
sample_num = int(input("Enter number of samples: "))

input_path = "../dataset/benchmark_fourth"
output_path = "../dataset/benchmark_result"
if not os.path.exists(output_path):
    os.mkdir(output_path)

client_qwen = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
client_deepseek = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)
client_gpt = OpenAI(
    api_key=os.getenv("GPT_API_KEY"),
    base_url="https://xiaoai.plus/v1"
)
client_o4 = OpenAI(
    api_key=os.getenv("O4_API_KEY"),
    base_url="https://api.b3n.fun/v1"
)

headers = {
    "Authorization": "Bearer " + os.getenv("HASH070_API_KEY", "")
}

def generate_client(model, prompt, Client, top_p, temperature):
    completion = Client.chat.completions.create(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are a Solidity smart contract development expert.'},
            {'role': 'user', 'content': prompt}
        ],
        top_p=top_p,
        temperature=temperature,
    )
    return completion.choices[0].message.content

def generate_response(model, prompt):
    params = {
        "messages": [
            {'role': 'system', 'content': 'You are a Solidity smart contract development expert.'},
            {'role': 'user', 'content': prompt}
        ],
        "model": model
    }
    try:
        response = requests.post(
            "https://c-z0-api-01.hash070.com/v1/chat/completions",
            headers=headers,
            json=params,
            stream=False
        )
        res = response.json()
        return res['choices'][0]['message']['content']
    except Exception as e:
        print(e)
        return ""

def test():
    count = 0
    for contract in os.listdir(input_path):
        if contract.endswith("json"):
            count += 1
            address = os.path.splitext(contract)[0]
            print(f"{count} Generating for {address}")
            prompt_path = os.path.join(input_path, contract)
            with open(prompt_path, "r") as f:
                data = json.load(f)

            model = models[model_num]
            model_contract = model[model.rfind("/") + 1:]
            contract_folder = os.path.join(output_path, model_contract, address)
            os.makedirs(os.path.join(output_path, model_contract), exist_ok=True)
            os.makedirs(contract_folder, exist_ok=True)

            top_p = 1.0
            temperature = 0.0

            for i in range(sample_num):
                print(f"{i+1}th {model} generate")

                reg = 0
                while True:
                    if model == "deepseek-reasoner":
                        response_message = generate_client(model, data['prompt'], client_deepseek, top_p, temperature)
                    elif model in ["claude-3-7-sonnet-20250219", "gemini-2.0-flash-exp", "gpt-4o"]:
                        response_message = generate_client(model, data['prompt'], client_gpt, top_p, temperature)
                    elif model == "qwen2.5-coder-32b-instruct":
                        response_message = generate_client(model, data['prompt'], client_qwen, top_p, temperature)
                    elif model == "o4-mini":
                        response_message = generate_client(model, data['prompt'], client_o4, top_p, temperature)
                    if len(response_message) > 10:
                        break
                    else:
                        print("regenerate")
                        reg += 1
                        if reg > 2:
                            break

                with open(os.path.join(contract_folder, f"output{i+1}.txt"), "w") as f:
                    f.write(response_message)

            time.sleep(1)

test()
