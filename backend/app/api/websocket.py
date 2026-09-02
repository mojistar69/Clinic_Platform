from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)


class ConnectionManager:

    def __init__(self):
        self.queue_connections = defaultdict(set)
        self.patient_connections = defaultdict(set)

    # =====================================================
    # Queue connections
    # =====================================================

    async def connect_queue(
        self,
        websocket: WebSocket,
        doctor_id: int,
        queue_date: str
    ):
        await websocket.accept()

        key = self._queue_key(
            doctor_id,
            queue_date
        )

        self.queue_connections[key].add(
            websocket
        )

        print(
            "QUEUE CONNECTED:",
            key,
            "connections=",
            len(self.queue_connections[key])
        )

    def disconnect_queue(
        self,
        websocket: WebSocket,
        doctor_id: int,
        queue_date: str
    ):
        key = self._queue_key(
            doctor_id,
            queue_date
        )

        self.queue_connections[key].discard(
            websocket
        )

        print(
            "QUEUE DISCONNECTED:",
            key,
            "connections=",
            len(self.queue_connections.get(key, set()))
        )

        if not self.queue_connections.get(key):
            self.queue_connections.pop(
                key,
                None
            )

    # =====================================================
    # Patient connections
    # =====================================================

    async def connect_patient(
        self,
        websocket: WebSocket,
        appointment_id: int
    ):
        await websocket.accept()

        key = self._patient_key(
            appointment_id
        )

        self.patient_connections[key].add(
            websocket
        )

        print(
            "PATIENT CONNECTED:",
            key,
            "connections=",
            len(self.patient_connections[key])
        )

    def disconnect_patient(
        self,
        websocket: WebSocket,
        appointment_id: int
    ):
        key = self._patient_key(
            appointment_id
        )

        self.patient_connections[key].discard(
            websocket
        )

        print(
            "PATIENT DISCONNECTED:",
            key,
            "connections=",
            len(self.patient_connections.get(key, set()))
        )

        if not self.patient_connections.get(key):
            self.patient_connections.pop(
                key,
                None
            )

    # =====================================================
    # Broadcast to queue clients
    # =====================================================

    async def broadcast_queue(
        self,
        doctor_id: int,
        queue_date: str,
        message: dict
    ):
        key = self._queue_key(
            doctor_id,
            queue_date
        )

        # IMPORTANT:
        # connections MUST be created before len()
        connections = list(
            self.queue_connections.get(
                key,
                set()
            )
        )

        print(
            "BROADCAST QUEUE:",
            key,
            "connections=",
            len(connections),
            "message_type=",
            message.get("type")
        )

        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(
                    message
                )

            except Exception as e:
                print(
                    "QUEUE SEND ERROR:",
                    e
                )

                disconnected.append(
                    websocket
                )

        for websocket in disconnected:
            self.queue_connections[key].discard(
                websocket
            )

        if not self.queue_connections.get(key):
            self.queue_connections.pop(
                key,
                None
            )

    # =====================================================
    # Broadcast to patient clients
    # =====================================================

    async def broadcast_patient(
        self,
        appointment_id: int,
        message: dict
    ):
        key = self._patient_key(
            appointment_id
        )

        connections = list(
            self.patient_connections.get(
                key,
                set()
            )
        )

        print(
            "BROADCAST PATIENT:",
            key,
            "connections=",
            len(connections),
            "message_type=",
            message.get("type")
        )

        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(
                    message
                )

            except Exception as e:
                print(
                    "PATIENT SEND ERROR:",
                    e
                )

                disconnected.append(
                    websocket
                )

        for websocket in disconnected:
            self.patient_connections[key].discard(
                websocket
            )

        if not self.patient_connections.get(key):
            self.patient_connections.pop(
                key,
                None
            )

    # =====================================================
    # Helpers
    # =====================================================

    @staticmethod
    def _queue_key(
        doctor_id: int,
        queue_date: str
    ):
        return f"{doctor_id}:{queue_date}"

    @staticmethod
    def _patient_key(
        appointment_id: int
    ):
        return str(appointment_id)


manager = ConnectionManager()


# =========================================================
# Queue WebSocket
# =========================================================

@router.websocket(
    "/queue/{doctor_id}/{queue_date}"
)
async def queue_websocket(
    websocket: WebSocket,
    doctor_id: int,
    queue_date: str
):
    await manager.connect_queue(
        websocket,
        doctor_id,
        queue_date
    )

    try:

        await websocket.send_json({
            "type": "CONNECTED",
            "doctor_id": doctor_id,
            "queue_date": queue_date,
            "message": "Queue monitoring connected"
        })

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:

        manager.disconnect_queue(
            websocket,
            doctor_id,
            queue_date
        )

    except Exception as e:

        print(
            "QUEUE WEBSOCKET ERROR:",
            e
        )

        manager.disconnect_queue(
            websocket,
            doctor_id,
            queue_date
        )


# =========================================================
# Patient WebSocket
# =========================================================

@router.websocket(
    "/patient/{appointment_id}"
)
async def patient_websocket(
    websocket: WebSocket,
    appointment_id: int
):
    await manager.connect_patient(
        websocket,
        appointment_id
    )

    try:

        await websocket.send_json({
            "type": "CONNECTED",
            "appointment_id": appointment_id,
            "message": "Patient monitoring connected"
        })

        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:

        manager.disconnect_patient(
            websocket,
            appointment_id
        )

    except Exception as e:

        print(
            "PATIENT WEBSOCKET ERROR:",
            e
        )

        manager.disconnect_patient(
            websocket,
            appointment_id
        )