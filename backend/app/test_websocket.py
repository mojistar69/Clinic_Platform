import asyncio
import websockets


async def main():
    uri = "ws://127.0.0.1:8000/ws/queue/25/1405-06-07"

    async with websockets.connect(uri) as websocket:

        print("Connected!")

        while True:
            message = await websocket.recv()
            print("MESSAGE:")
            print(message)


asyncio.run(main())