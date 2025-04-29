from fastapi import WebSocket, WebSocketDisconnect

# List to store all connected clients
connected_clients = []


async def connect(websocket: WebSocket):
    """Connect a new WebSocket client."""
    await websocket.accept()
    connected_clients.append(websocket)
    return websocket


async def disconnect(websocket: WebSocket):
    """Disconnect a WebSocket client."""
    if websocket in connected_clients:
        connected_clients.remove(websocket)


async def handle_websocket_connection(websocket: WebSocket):
    """Handle WebSocket connection lifecycle."""
    await connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        await disconnect(websocket)
