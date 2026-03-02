"""
User WebSocket Routes (Version 1)

Real-time WebSocket endpoints for user-related operations.
"""

import asyncio
import json
from loguru import logger
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["websockets"])


class UserConnectionManager:
    """Connection manager for user-related WebSocket connections"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[str] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            self.user_connections[user_id] = websocket
        logger.info(
            f"✅ User WebSocket connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket, user_id: Optional[str] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            del self.user_connections[user_id]
        logger.info(
            f"❌ User WebSocket disconnected. Total connections: {len(self.active_connections)}"
        )

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_personal_json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)

    async def broadcast_to_users(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user: {e}")

    async def send_to_user(self, user_id: str, message: str):
        if user_id in self.user_connections:
            try:
                await self.user_connections[user_id].send_text(message)
                return True
            except Exception as e:
                logger.error(f"Error sending to user {user_id}: {e}")
                return False
        return False


# Global connection manager for users
user_manager = UserConnectionManager()


@router.websocket("/users/{user_id}")
async def user_websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for user-specific real-time communication
    """
    await user_manager.connect(websocket, user_id)

    try:
        # Send welcome message
        await user_manager.send_personal_json(
            {
                "type": "connection",
                "message": f"Welcome user {user_id}!",
                "user_id": user_id,
                "timestamp": asyncio.get_event_loop().time(),
            },
            websocket,
        )

        while True:
            # Wait for message from client
            data = await websocket.receive_text()

            try:
                # Parse JSON if possible
                message_data = json.loads(data)
                message_type = message_data.get("type", "message")

                if message_type == "ping":
                    # Handle ping/pong
                    await user_manager.send_personal_json(
                        {"type": "pong", "timestamp": asyncio.get_event_loop().time()},
                        websocket,
                    )

                elif message_type == "broadcast":
                    # Broadcast message to all connected users
                    broadcast_msg = f"User {user_id}: {message_data.get('message', '')}"
                    await user_manager.broadcast_to_users(broadcast_msg)

                elif message_type == "private":
                    # Send private message to specific user
                    target_user = message_data.get("target_user")
                    message = message_data.get("message", "")

                    if target_user:
                        private_msg = f"Private from {user_id}: {message}"
                        sent = await user_manager.send_to_user(target_user, private_msg)

                        # Confirm delivery
                        await user_manager.send_personal_json(
                            {
                                "type": "delivery_status",
                                "target_user": target_user,
                                "delivered": sent,
                                "timestamp": asyncio.get_event_loop().time(),
                            },
                            websocket,
                        )

                else:
                    # Echo back the message
                    await user_manager.send_personal_json(
                        {
                            "type": "echo",
                            "original_message": message_data,
                            "user_id": user_id,
                            "timestamp": asyncio.get_event_loop().time(),
                        },
                        websocket,
                    )

            except json.JSONDecodeError:
                # Handle plain text messages
                await user_manager.send_personal_json(
                    {
                        "type": "text_received",
                        "message": f"Received: {data}",
                        "user_id": user_id,
                        "timestamp": asyncio.get_event_loop().time(),
                    },
                    websocket,
                )

    except WebSocketDisconnect:
        user_manager.disconnect(websocket, user_id)
        logger.info(f"User {user_id} disconnected")

    except Exception as e:
        logger.error(f"Error in user WebSocket {user_id}: {e}")
        user_manager.disconnect(websocket, user_id)


@router.websocket("/users/general")
async def general_user_websocket(websocket: WebSocket):
    """
    General WebSocket endpoint for anonymous user connections
    """
    await user_manager.connect(websocket)

    try:
        # Send welcome message
        await user_manager.send_personal_json(
            {
                "type": "connection",
                "message": "Welcome to general user channel!",
                "timestamp": asyncio.get_event_loop().time(),
            },
            websocket,
        )

        while True:
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)

                if message_data.get("type") == "ping":
                    await user_manager.send_personal_json(
                        {"type": "pong", "timestamp": asyncio.get_event_loop().time()},
                        websocket,
                    )
                else:
                    # Broadcast to all general connections
                    await user_manager.broadcast_to_users(
                        f"Anonymous: {message_data.get('message', data)}"
                    )

            except json.JSONDecodeError:
                await user_manager.broadcast_to_users(f"Anonymous: {data}")

    except WebSocketDisconnect:
        user_manager.disconnect(websocket)
        logger.info("Anonymous user disconnected")

    except Exception as e:
        logger.error(f"Error in general user WebSocket: {e}")
        user_manager.disconnect(websocket)
