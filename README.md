# Discord Friends Remover

A desktop utility for bulk-managing and removing Discord friends and stale direct messages. Connects through a user token, indexes the full relationship list with DM activity timestamps, and executes removals with safe, rate-limited intervals.

---

## Key Features

- **Token Authentication**: Validates the user token against Discord's API and loads the full friend list on login.
- **DM Activity Tracking**: Cross-references each friend against DM channel history using snowflake timestamps to determine last message activity.
- **Unfriended DM Management**: Scans open direct message channels to identify users who are no longer on your friends list, allowing you to close stale DM channels individually or in bulk.
- **Filter Tabs**: Segments entries into All Friends, Active, Never Messaged, and Unfriended DMs with live count badges.
- **Direct Row Removal**: Quick-action button on each card to immediately close a DM or remove a friend with a single click.
- **Search**: Real-time filtering by display name or username across all views.
- **Bulk Selection**: Select All / Deselect All with individual checkbox overrides and a live selection counter.
- **Rate-Limited Execution**: Executes deletions sequentially with safe intervals between requests. Automatically retries on 429 responses using the server-provided `Retry-After` value.
- **Progress Tracking**: Modal progress dialog with per-item status updates and cancellation support.

---

## Prerequisites

- **Python**: 3.10 or higher

---

## Installation & Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run:
   ```bash
   python main.py
   ```

3. Paste your Discord user token and click Login.

---

## Getting Your Token

1. Open Discord in a web browser
2. Open Developer Tools (F12) and go to the Network tab
3. Send a message in any channel
4. Find a request to `discord.com/api` and copy the `Authorization` header value

Do not share your token with anyone.

---

## Project Structure

```
main.py            Entry point
discord_api.py     API wrapper
gui.py             Desktop interface (CustomTkinter)
requirements.txt   Dependencies
```

---

## Disclaimer

Using a user token for automation violates Discord's Terms of Service. Use at your own risk.

---

## License

MIT
