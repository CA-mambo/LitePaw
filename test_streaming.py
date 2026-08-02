import asyncio
import json
import websockets
import time

async def test():
    async with websockets.connect('ws://localhost:8765/ws/chat') as ws:
        await ws.send(json.dumps({'content': '你好'}))
        timestamps = []
        async for msg in ws:
            data = json.loads(msg)
            now = time.time()
            timestamps.append(now)
            if data['type'] == 'chunk' and data.get('content'):
                print(f'[{len(timestamps):3d}] +{now - timestamps[0]:.3f}s | {repr(data["content"][:30])}', flush=True)
            if data['type'] == 'done':
                break
        
        if len(timestamps) > 1:
            gaps = [timestamps[i] - timestamps[i-1] for i in range(1, len(timestamps))]
            print(f'\nTotal chunks: {len(timestamps)}')
            print(f'Total time: {timestamps[-1] - timestamps[0]:.3f}s')
            print(f'Avg gap: {sum(gaps)/len(gaps)*1000:.1f}ms')
            print(f'Min gap: {min(gaps)*1000:.1f}ms')
            print(f'Max gap: {max(gaps)*1000:.1f}ms', flush=True)

asyncio.run(test())
