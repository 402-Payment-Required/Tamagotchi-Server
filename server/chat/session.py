import uuid

# session_id -> {user_id, history: [{role, content}, ...]}
_sessions: dict[str, dict] = {}


def start_session(user_id: str) -> str:
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {"user_id": user_id, "history": []}
    return session_id


def get_history(session_id: str) -> list:
    return _sessions.get(session_id, {}).get("history", [])


def add_turn(session_id: str, role: str, content: str) -> None:
    if session_id in _sessions:
        _sessions[session_id]["history"].append({"role": role, "content": content})


def end_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
