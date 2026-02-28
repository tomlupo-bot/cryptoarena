#!/bin/bash
# Start MCP tool servers for CryptoArena
cd /home/node/.openclaw/repos/cryptoarena
export PYTHONPATH="/tmp/pylibs:$PWD"
export CRYPTO_HTTP_PORT=8005

for tool in tool_math tool_get_price_local tool_crypto_trade tool_indicators tool_portfolio; do
    python3 agent_tools/${tool}.py > /tmp/mcp_${tool}.log 2>&1 &
    echo "Started $tool (pid $!)"
done
sleep 3

echo "Checking ports..."
python3 -c "
import socket
for port in [8000,8003,8005,8006,8007]:
    s=socket.socket(); s.settimeout(0.5)
    r=s.connect_ex(('127.0.0.1',port)); s.close()
    print(f'  Port {port}: UP' if r==0 else f'  Port {port}: DOWN')"
