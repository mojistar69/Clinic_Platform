from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)


class ConnectionManager:
    def __init__(self):
        # queue_key -> connected clients
        self.queue_connections = defaultdict(set)

        # patient_key -> connected clients
        self.patient_connections = defaultdict(set)

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

        if not self.queue_connections[key]:
            del self.queue_connections[key]

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

        if not self.patient_connections[key]:
            del self.patient_connections[key]

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

        connections = list(
            self.queue_connections.get(
                key,
                set()
            )
        )

        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(
                    message
                )
            except Exception:
                disconnected.append(
                    websocket
                )

        for websocket in disconnected:
            self.queue_connections[key].discard(
                websocket
            )

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

        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(
                    message
                )
            except Exception:
                disconnected.append(
                    websocket
                )

        for websocket in disconnected:
            self.patient_connections[key].discard(
                websocket
            )

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

    except Exception:
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

    except Exception:
        manager.disconnect_patient(
            websocket,
            appointment_id
        )