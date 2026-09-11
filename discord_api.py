import time
import requests
from datetime import datetime, timezone


class DiscordAPI:
    BASE_URL = "https://discord.com/api/v10"
    CDN_URL = "https://cdn.discordapp.com"

    FRIEND = 1
    BLOCKED = 2
    INCOMING_REQUEST = 3
    OUTGOING_REQUEST = 4

    def __init__(self, token):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": token,
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })

    def get_current_user(self):
        resp = self.session.get(f"{self.BASE_URL}/users/@me")
        resp.raise_for_status()
        return resp.json()

    def get_relationships(self):
        resp = self.session.get(f"{self.BASE_URL}/users/@me/relationships")
        resp.raise_for_status()
        return resp.json()

    def get_friends(self):
        return [r for r in self.get_relationships() if r.get("type") == self.FRIEND]

    def delete_friend(self, user_id):
        resp = self.session.delete(f"{self.BASE_URL}/users/@me/relationships/{user_id}")
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            time.sleep(retry_after)
            return self.delete_friend(user_id)
        resp.raise_for_status()
        return True

    def close_dm(self, channel_id):
        resp = self.session.delete(f"{self.BASE_URL}/channels/{channel_id}")
        if resp.status_code == 429:
            retry_after = resp.json().get("retry_after", 5)
            time.sleep(retry_after)
            return self.close_dm(channel_id)
        resp.raise_for_status()
        return True

    def get_dm_channels(self):
        resp = self.session.get(f"{self.BASE_URL}/users/@me/channels")
        resp.raise_for_status()
        return resp.json()

    def get_avatar_url(self, user_id, avatar_hash, discriminator="0", size=128):
        if avatar_hash:
            ext = "gif" if avatar_hash.startswith("a_") else "png"
            return f"{self.CDN_URL}/avatars/{user_id}/{avatar_hash}.{ext}?size={size}"
        if discriminator and discriminator != "0":
            index = int(discriminator) % 5
        else:
            index = (int(user_id) >> 22) % 6
        return f"{self.CDN_URL}/embed/avatars/{index}.png"

    @staticmethod
    def snowflake_to_datetime(snowflake_id):
        if not snowflake_id:
            return None
        ts = (int(snowflake_id) >> 22) + 1420070400000
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc)

    @staticmethod
    def time_ago(dt):
        if dt is None:
            return "Never"
        diff = datetime.now(tz=timezone.utc) - dt
        secs = int(diff.total_seconds())
        if secs < 60:
            return "Just now"
        mins = secs // 60
        if mins < 60:
            return f"{mins}m ago"
        hrs = mins // 60
        if hrs < 24:
            return f"{hrs}h ago"
        days = hrs // 24
        if days < 30:
            return f"{days}d ago"
        months = days // 30
        if months < 12:
            return f"{months}mo ago"
        return f"{months // 12}y ago"
