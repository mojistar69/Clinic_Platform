import asyncio
import websockets


async def main():
    uri = "ws://127.0.0.1:8000/ws/patient/15"

    async with websockets.connect(uri) as websocket:

        print("Patient WebSocket connected!")

        while True:
            message = await websocket.recv()
            print("MESSAGE:")
            print(message)


asyncio.run(main())