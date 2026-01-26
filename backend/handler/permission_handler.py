class PermissionHandler:
    def __init__(self, config: dict):
        self.config = config["bilibili"]
        self.song_permission = self.config["song_request_permission"]
        self.next_permission = self.config["next_request_permission"]

    def is_allowed(self, request: dict) -> bool:
        user = request.get("user", {})
        req = request.get("request", {})
        req_type = req.get("type")

        if user.get("is_streamer", 0) == 1:
            return True

        if req_type == "song":
            perm = self.song_permission
        elif req_type == "next":
            perm = self.next_permission
        else:
            return False

        if perm.get("streamer", False) and user.get("is_streamer", 0) == 1:
            return True
        if perm.get("room_admin", False) and user.get("admin", 0) == 1:
            return True
        if perm.get("guard", False) and user.get("privilege_type", 0) > 0:
            return True
        if "medal_level" in perm:
            try:
                required = int(perm["medal_level"])
                if user.get("medal_level", 0) >= required:
                    return True
            except (ValueError, TypeError):
                pass
        return False
