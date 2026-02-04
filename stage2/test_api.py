"""
API测试脚本
"""
import sys
import time
import subprocess
import requests
import json

# 启动API服务器
print("Starting API server...")
server_process = subprocess.Popen([
    sys.executable, "-m", "src.api.server",
    "--db", "./data/demo_indexer.db",
    "--port", "8000"
], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# 等待服务器启动
time.sleep(3)

try:
    print("\n=== Testing API Endpoints ===\n")
    
    # 测试根路径
    print("1. Testing GET /")
    response = requests.get("http://127.0.0.1:8000/")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    
    # 测试获取市场信息
    print("2. Testing GET /markets/{slug}")
    response = requests.get("http://127.0.0.1:8000/markets/will-there-be-another-us-government-shutdown-by-january-31")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    
    # 测试获取交易记录
    print("3. Testing GET /markets/{slug}/trades")
    response = requests.get("http://127.0.0.1:8000/markets/will-there-be-another-us-government-shutdown-by-january-31/trades?limit=5")
    print(f"Status: {response.status_code}")
    trades = response.json()
    print(f"Response: Found {len(trades)} trades")
    if trades:
        print(f"First trade: {json.dumps(trades[0], indent=2)}\n")
    
    # 测试按token_id查询交易
    print("4. Testing GET /tokens/{token_id}/trades")
    token_id = "0x744eaf8517da344aefb0956978e0cae7bb9c2fefb183740197f0127d86b0bcbd"
    response = requests.get(f"http://127.0.0.1:8000/tokens/{token_id}/trades?limit=5")
    print(f"Status: {response.status_code}")
    trades = response.json()
    print(f"Response: Found {len(trades)} trades for token\n")
    
    print("✓ All API tests passed!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    # 停止服务器
    print("\nStopping API server...")
    server_process.terminate()
    server_process.wait()
    print("Done!")
