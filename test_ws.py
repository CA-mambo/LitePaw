import asyncio
import json
import websockets

async def test():
    uri = "ws://localhost:8765/ws/chat"
    print(f"Connecting to {uri}...")
    
    async with websockets.connect(uri) as ws:
        print("✅ WS CONNECTED")
        
        await ws.send(json.dumps({"content": "你好，测试连通性"}))
        print("📤 Sent: 你好，测试连通性")
        
        chunks = []
        async for msg in ws:
            data = json.loads(msg)
            msg_type = data.get("type", "unknown")
            content = data.get("content", "")[:60]
            print(f"📥 RECV [{msg_type}]: {content}")
            chunks.append(data)
            
            if data.get("done"):
                session_id = data.get("session_id", "")
                print(f"✅ DONE - session: {session_id}")
                print(f"📊 Total chunks received: {len(chunks)}")
                return True
        
    return False

try:
    result = asyncio.run(test())
    if result:
        print("\n 端到端连通性测试通过！")
    else:
        print("\n❌ 测试失败")
except Exception as e:
    print(f"\n❌ 测试异常: {e}")
    raise
