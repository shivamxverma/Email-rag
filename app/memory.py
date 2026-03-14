import uuid

sessions = {}


def start_session(thread_id):

    session_id = str(uuid.uuid4())

    sessions[session_id] = {
        "thread_id": thread_id,
        "history": []
    }

    return session_id


def update_memory(session_id, user, answer):

    sessions[session_id]["history"].append({
        "user": user,
        "assistant": answer
    })

    sessions[session_id]["history"] = sessions[session_id]["history"][-5:]