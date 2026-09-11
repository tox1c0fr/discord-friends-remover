import io
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import customtkinter as ctk
import requests
from PIL import Image, ImageDraw

from discord_api import DiscordAPI

BG = "#1e1f22"
CARD = "#2b2d31"
CARD_HOVER = "#35373c"
INPUT_BG = "#1e1f22"
ACCENT = "#5865f2"
ACCENT_HOVER = "#4752c4"
DANGER = "#da373c"
DANGER_HOVER = "#a12d31"
SUCCESS = "#23a55a"
WARNING = "#f0b232"
TEXT_PRIMARY = "#f2f3f5"
TEXT_SECONDARY = "#b5bac1"
TEXT_MUTED = "#949ba4"
FONT = "Segoe UI"


class ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, btn_text="Remove"):
        super().__init__(parent)
        self.result = False
        self.title(title)
        self.geometry("420x200")
        self.resizable(False, False)
        self.configure(fg_color=CARD)
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 420) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 200) // 2
        self.geometry(f"+{px}+{py}")

        ctk.CTkLabel(
            self, text=title, font=(FONT, 16, "bold"), text_color=TEXT_PRIMARY
        ).pack(pady=(24, 8))

        ctk.CTkLabel(
            self, text=message, font=(FONT, 13), text_color=TEXT_MUTED, wraplength=360
        ).pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=30, pady=(0, 20))

        ctk.CTkButton(
            btn_frame, text="Cancel", width=120, height=36,
            fg_color=CARD_HOVER, hover_color="#3f4147",
            font=(FONT, 13), command=self._cancel,
        ).pack(side="left", expand=True, padx=5)

        ctk.CTkButton(
            btn_frame, text=btn_text, width=120, height=36,
            fg_color=DANGER, hover_color=DANGER_HOVER,
            font=(FONT, 13, "bold"), command=self._confirm,
        ).pack(side="right", expand=True, padx=5)

        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def _confirm(self):
        self.result = True
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = False
        self.grab_release()
        self.destroy()


class ProgressDialog(ctk.CTkToplevel):
    def __init__(self, parent, total, title="Removing Friends", action_word="removed"):
        super().__init__(parent)
        self.title(title)
        self.geometry("460x220")
        self.resizable(False, False)
        self.configure(fg_color=CARD)
        self.transient(parent)
        self.grab_set()
        self.total = total
        self.action_word = action_word
        self.cancelled = False

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 460) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 220) // 2
        self.geometry(f"+{px}+{py}")

        ctk.CTkLabel(
            self, text=title, font=(FONT, 16, "bold"), text_color=TEXT_PRIMARY
        ).pack(pady=(24, 12))

        self.status_label = ctk.CTkLabel(
            self, text=f"0 / {total}", font=(FONT, 13), text_color=TEXT_MUTED
        )
        self.status_label.pack(pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(
            self, width=380, height=12, progress_color=ACCENT, fg_color=BG
        )
        self.progress_bar.pack(pady=(0, 16))
        self.progress_bar.set(0)

        self.cancel_btn = ctk.CTkButton(
            self, text="Cancel", width=120, height=34,
            fg_color=CARD_HOVER, hover_color="#3f4147",
            font=(FONT, 13), command=self._cancel,
        )
        self.cancel_btn.pack()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

    def update_progress(self, current, username=""):
        self.progress_bar.set(current / self.total if self.total else 1)
        self.status_label.configure(text=f"{current} / {self.total}  -  {username}")

    def mark_complete(self):
        self.status_label.configure(text=f"Done - {self.action_word} {self.total}", text_color=SUCCESS)
        self.cancel_btn.configure(text="Close", command=self._close)
        self.progress_bar.set(1)

    def _cancel(self):
        self.cancelled = True
        self.grab_release()
        self.destroy()

    def _close(self):
        self.grab_release()
        self.destroy()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Discord Friends Remover")
        self.geometry("960x700")
        self.minsize(860, 600)
        self.configure(fg_color=BG)
        ctk.set_appearance_mode("dark")

        self.api = None
        self.user_info = {}
        self.friends_data = []
        self.stale_dms = []
        self.dm_activity = {}
        self.selected_ids = set()
        self.avatar_images = {}
        self.card_widgets = {}
        self.current_filter = "all"

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._render_items())

        self.executor = ThreadPoolExecutor(max_workers=10)
        self._placeholder = self._make_placeholder()

        self._build_login()
        self._build_dashboard()
        self._show_login()

    @staticmethod
    def _make_placeholder():
        img = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, 39, 39), fill=(55, 57, 63))
        draw.ellipse((14, 8, 26, 20), fill=(113, 118, 128))
        draw.chord((8, 22, 32, 42), 0, 180, fill=(113, 118, 128))
        return ctk.CTkImage(light_image=img, dark_image=img, size=(40, 40))

    def _build_login(self):
        self.login_frame = ctk.CTkFrame(self, fg_color="transparent")

        card = ctk.CTkFrame(self.login_frame, fg_color=CARD, corner_radius=12, width=420, height=370)
        card.place(relx=0.5, rely=0.5, anchor="center")
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=40, pady=32)

        ctk.CTkLabel(
            inner, text="Discord Friends Remover",
            font=(FONT, 20, "bold"), text_color=TEXT_PRIMARY
        ).pack(pady=(10, 28))

        ctk.CTkLabel(
            inner, text="DISCORD TOKEN",
            font=(FONT, 11, "bold"), text_color=TEXT_MUTED, anchor="w"
        ).pack(fill="x")

        self.token_entry = ctk.CTkEntry(
            inner, placeholder_text="Paste your token here",
            height=42, font=(FONT, 13), show="\u2022",
            fg_color=INPUT_BG, border_color=CARD_HOVER, border_width=1,
        )
        self.token_entry.pack(fill="x", pady=(6, 6))
        self.token_entry.bind("<Return>", lambda _: self._on_login())

        self._show_token = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            inner, text="Show token", variable=self._show_token,
            command=self._toggle_token, font=(FONT, 11),
            text_color=TEXT_MUTED, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            checkbox_width=18, checkbox_height=18,
        ).pack(anchor="w", pady=(0, 20))

        self.login_btn = ctk.CTkButton(
            inner, text="Login", height=42, font=(FONT, 14, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER, command=self._on_login,
        )
        self.login_btn.pack(fill="x", pady=(0, 12))

        self.login_status = ctk.CTkLabel(inner, text="", font=(FONT, 12), text_color=DANGER)
        self.login_status.pack()

        ctk.CTkLabel(
            inner, text="Token is not stored or logged",
            font=(FONT, 11), text_color=TEXT_MUTED
        ).pack(side="bottom", pady=(8, 0))

    def _build_dashboard(self):
        self.dashboard_frame = ctk.CTkFrame(self, fg_color="transparent")

        header = ctk.CTkFrame(self.dashboard_frame, fg_color=CARD, corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="both", expand=True, padx=20)

        self.header_avatar = ctk.CTkLabel(header_inner, text="", width=36, height=36, image=self._placeholder)
        self.header_avatar.pack(side="left", padx=(0, 10))

        info = ctk.CTkFrame(header_inner, fg_color="transparent")
        info.pack(side="left", fill="y")

        self.header_name = ctk.CTkLabel(info, text="", font=(FONT, 14, "bold"), text_color=TEXT_PRIMARY, anchor="w")
        self.header_name.pack(anchor="w")

        self.header_count = ctk.CTkLabel(info, text="", font=(FONT, 11), text_color=TEXT_MUTED, anchor="w")
        self.header_count.pack(anchor="w")

        ctk.CTkButton(
            header_inner, text="Logout", width=80, height=32,
            font=(FONT, 12), fg_color=CARD_HOVER, hover_color="#3f4147",
            command=self._logout,
        ).pack(side="right")

        controls = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        controls.pack(fill="x", padx=16, pady=(12, 6))

        self.search_entry = ctk.CTkEntry(
            controls, textvariable=self.search_var,
            placeholder_text="Search...",
            height=36, width=230, font=(FONT, 13),
            fg_color=CARD, border_color=CARD_HOVER, border_width=1,
        )
        self.search_entry.pack(side="left")

        filters = ctk.CTkFrame(controls, fg_color="transparent")
        filters.pack(side="right")

        self.filter_btns = {}
        for key, label, w in [
            ("all", "All", 80),
            ("active", "Active", 100),
            ("inactive", "Never Messaged", 135),
            ("stale_dms", "Unfriended DMs", 135),
        ]:
            btn = ctk.CTkButton(
                filters, text=label, height=32, width=w,
                font=(FONT, 12),
                fg_color=ACCENT if key == "all" else CARD_HOVER,
                hover_color=ACCENT_HOVER,
                command=lambda k=key: self._set_filter(k),
            )
            btn.pack(side="left", padx=2)
            self.filter_btns[key] = btn

        self.scroll = ctk.CTkScrollableFrame(
            self.dashboard_frame, fg_color=BG,
            scrollbar_button_color=CARD_HOVER,
            scrollbar_button_hover_color="#3f4147",
        )
        self.scroll.pack(fill="both", expand=True, padx=16, pady=(4, 4))

        action = ctk.CTkFrame(self.dashboard_frame, fg_color=CARD, corner_radius=0, height=56)
        action.pack(fill="x", side="bottom")
        action.pack_propagate(False)

        action_inner = ctk.CTkFrame(action, fg_color="transparent")
        action_inner.pack(fill="both", expand=True, padx=20)

        ctk.CTkButton(
            action_inner, text="Select All", width=90, height=32,
            font=(FONT, 12), fg_color=CARD_HOVER, hover_color="#3f4147",
            command=self._select_all,
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            action_inner, text="Deselect All", width=100, height=32,
            font=(FONT, 12), fg_color=CARD_HOVER, hover_color="#3f4147",
            command=self._deselect_all,
        ).pack(side="left", padx=(0, 14))

        self.sel_label = ctk.CTkLabel(
            action_inner, text="0 selected", font=(FONT, 13), text_color=TEXT_MUTED
        )
        self.sel_label.pack(side="left")

        self.del_btn = ctk.CTkButton(
            action_inner, text="Remove Selected", height=36, width=170,
            font=(FONT, 13, "bold"), fg_color=DANGER, hover_color=DANGER_HOVER,
            command=self._on_delete,
        )
        self.del_btn.pack(side="right")

    def _show_login(self):
        self.dashboard_frame.pack_forget()
        self.login_frame.pack(fill="both", expand=True)
        self.token_entry.focus_set()

    def _show_dashboard(self):
        self.login_frame.pack_forget()
        self.dashboard_frame.pack(fill="both", expand=True)

    def _toggle_token(self):
        self.token_entry.configure(show="" if self._show_token.get() else "\u2022")

    def _on_login(self):
        token = self.token_entry.get().strip()
        if not token:
            self.login_status.configure(text="Enter your token.", text_color=DANGER)
            return
        self.login_btn.configure(state="disabled", text="Logging in...")
        self.login_status.configure(text="")
        threading.Thread(target=self._login_worker, args=(token,), daemon=True).start()

    def _login_worker(self, token):
        try:
            api = DiscordAPI(token)
            user = api.get_current_user()
            friends = api.get_friends()
            channels = api.get_dm_channels()

            friend_ids = {f["user"]["id"] for f in friends}
            dm_map = {}
            stale_dms = []
            curr_id = user.get("id")

            for ch in channels:
                if ch.get("type") == 1:
                    recips = ch.get("recipients", [])
                    if recips:
                        recip = recips[0]
                        uid = recip.get("id")
                        last_dt = DiscordAPI.snowflake_to_datetime(ch.get("last_message_id"))
                        dm_map[uid] = last_dt
                        if uid not in friend_ids and uid != curr_id:
                            stale_dms.append({
                                "channel_id": ch["id"],
                                "user": recip,
                                "last_message_id": ch.get("last_message_id"),
                                "last_dm": last_dt,
                            })

            self.after(0, self._on_login_ok, api, user, friends, stale_dms, dm_map)

        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 401:
                msg = "Invalid token."
            elif code == 403:
                msg = "Access denied."
            else:
                msg = f"HTTP {code}"
            self.after(0, self._on_login_fail, msg)
        except requests.exceptions.ConnectionError:
            self.after(0, self._on_login_fail, "Connection failed.")
        except Exception as e:
            self.after(0, self._on_login_fail, str(e))

    def _on_login_ok(self, api, user, friends, stale_dms, dm_map):
        self.api = api
        self.user_info = user
        self.friends_data = friends
        self.stale_dms = stale_dms
        self.dm_activity = dm_map
        self.selected_ids.clear()
        self.avatar_images.clear()
        self.card_widgets.clear()

        name = user.get("global_name") or user.get("username", "User")
        self.header_name.configure(text=name)

        self.executor.submit(
            self._load_avatar, user["id"], user.get("avatar"),
            user.get("discriminator", "0"), self.header_avatar,
        )

        self._update_filter_counts()
        self._show_dashboard()
        self._render_items()
        self.login_btn.configure(state="normal", text="Login")

    def _on_login_fail(self, msg):
        self.login_status.configure(text=msg, text_color=DANGER)
        self.login_btn.configure(state="normal", text="Login")

    def _logout(self):
        self.api = None
        self.user_info = {}
        self.friends_data = []
        self.stale_dms = []
        self.dm_activity = {}
        self.selected_ids.clear()
        self.avatar_images.clear()
        self.card_widgets.clear()
        self.token_entry.delete(0, "end")
        self.login_status.configure(text="")
        self._show_login()

    def _set_filter(self, key):
        switching_mode = (self.current_filter == "stale_dms") != (key == "stale_dms")
        self.current_filter = key
        if switching_mode:
            self.selected_ids.clear()
        for k, btn in self.filter_btns.items():
            btn.configure(fg_color=ACCENT if k == key else CARD_HOVER)
        self._render_items()

    def _update_filter_counts(self):
        total_friends = len(self.friends_data)
        active = sum(1 for f in self.friends_data if self.dm_activity.get(f["user"]["id"]) is not None)
        inactive = total_friends - active
        stale = len(self.stale_dms)
        self.filter_btns["all"].configure(text=f"All ({total_friends})")
        self.filter_btns["active"].configure(text=f"Active ({active})")
        self.filter_btns["inactive"].configure(text=f"Never Messaged ({inactive})")
        self.filter_btns["stale_dms"].configure(text=f"Unfriended DMs ({stale})")
        self.header_count.configure(
            text=f"{total_friends} friends  \u2022  {stale} unfriended DMs"
        )

    def _filtered_items(self):
        query = self.search_var.get().lower().strip()
        out = []
        if self.current_filter == "stale_dms":
            for d in self.stale_dms:
                u = d.get("user", {})
                dname = (u.get("global_name") or u.get("username", "")).lower()
                uname = u.get("username", "").lower()
                if query and query not in dname and query not in uname:
                    continue
                out.append(d)
        else:
            for f in self.friends_data:
                u = f.get("user", {})
                uid = u.get("id", "")
                dname = (u.get("global_name") or u.get("username", "")).lower()
                uname = u.get("username", "").lower()
                if query and query not in dname and query not in uname:
                    continue
                has_dm = self.dm_activity.get(uid) is not None
                if self.current_filter == "active" and not has_dm:
                    continue
                if self.current_filter == "inactive" and has_dm:
                    continue
                out.append(f)
        return out

    def _render_items(self):
        for w in self.scroll.winfo_children():
            w.destroy()
        self.card_widgets.clear()

        items = self._filtered_items()
        if not items:
            empty_text = "No unfriended DMs found." if self.current_filter == "stale_dms" else "No friends found."
            ctk.CTkLabel(
                self.scroll, text=empty_text,
                font=(FONT, 14), text_color=TEXT_MUTED
            ).pack(pady=40)
            self._update_count()
            return

        is_stale = (self.current_filter == "stale_dms")
        for item in items:
            self._make_card(item, is_stale=is_stale)
        self._update_count()

    def _make_card(self, item, is_stale=False):
        if is_stale:
            item_id = item["channel_id"]
            u = item.get("user", {})
            uid = u.get("id", "")
            last_dm = item.get("last_dm")
            tag_text = "Unfriended"
        else:
            u = item.get("user", {})
            item_id = u.get("id", "")
            uid = item_id
            last_dm = self.dm_activity.get(uid)
            tag_text = "Last DM"

        dname = u.get("global_name") or u.get("username", "Unknown")
        uname = u.get("username", "")
        avatar_hash = u.get("avatar")
        disc = u.get("discriminator", "0")

        activity = DiscordAPI.time_ago(last_dm)
        if is_stale:
            activity_color = WARNING
        else:
            activity_color = TEXT_SECONDARY if last_dm else WARNING

        row = ctk.CTkFrame(self.scroll, fg_color=CARD, corner_radius=8, height=56)
        row.pack(fill="x", padx=4, pady=2)
        row.pack_propagate(False)

        row.bind("<Enter>", lambda _, r=row: r.configure(fg_color=CARD_HOVER))
        row.bind("<Leave>", lambda _, r=row: r.configure(fg_color=CARD))

        cb_var = ctk.BooleanVar(value=item_id in self.selected_ids)
        ctk.CTkCheckBox(
            row, text="", width=24, variable=cb_var,
            checkbox_width=18, checkbox_height=18,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=TEXT_MUTED,
            command=lambda: self._toggle(item_id, cb_var.get()),
        ).pack(side="left", padx=(12, 8), pady=8)

        av = ctk.CTkLabel(row, text="", width=40, height=40, image=self._placeholder)
        av.pack(side="left", padx=(0, 10))

        names = ctk.CTkFrame(row, fg_color="transparent")
        names.pack(side="left", fill="both", expand=True, pady=6)

        ctk.CTkLabel(
            names, text=dname, font=(FONT, 13, "bold"),
            text_color=TEXT_PRIMARY, anchor="w"
        ).pack(anchor="w")

        ctk.CTkLabel(
            names, text=f"@{uname}", font=(FONT, 11),
            text_color=TEXT_MUTED, anchor="w"
        ).pack(anchor="w")

        right_box = ctk.CTkFrame(row, fg_color="transparent")
        right_box.pack(side="right", padx=(4, 12))

        if is_stale:
            btn_cmd = lambda: self._close_single_dm(item_id, uname, row)
        else:
            btn_cmd = lambda: self._confirm_delete_single_friend(item_id, uname)

        ctk.CTkButton(
            right_box, text="\u2715", width=28, height=28, corner_radius=6,
            font=(FONT, 12, "bold"),
            fg_color="transparent", hover_color=DANGER,
            text_color=TEXT_MUTED,
            command=btn_cmd,
        ).pack(side="right", padx=(8, 0))

        act_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        act_frame.pack(side="right", padx=(0, 6))

        ctk.CTkLabel(act_frame, text=tag_text, font=(FONT, 10), text_color=TEXT_MUTED, anchor="e").pack(anchor="e")
        ctk.CTkLabel(act_frame, text=activity, font=(FONT, 12, "bold"), text_color=activity_color, anchor="e").pack(anchor="e")

        self.card_widgets[item_id] = {"row": row, "var": cb_var, "avatar": av}
        self.executor.submit(self._load_avatar, uid, avatar_hash, disc, av)

    def _load_avatar(self, user_id, avatar_hash, discriminator, label):
        try:
            url = self.api.get_avatar_url(user_id, avatar_hash, discriminator)
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()

            img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            img = img.resize((40, 40), Image.Resampling.LANCZOS)

            mask = Image.new("L", (40, 40), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 39, 39), fill=255)
            out = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
            out.paste(img, (0, 0), mask)

            ctk_img = ctk.CTkImage(light_image=out, dark_image=out, size=(40, 40))
            self.avatar_images[user_id] = ctk_img
            self.after(0, lambda: self._set_avatar(label, ctk_img))
        except Exception:
            pass

    def _set_avatar(self, label, img):
        try:
            label.configure(image=img)
        except Exception:
            pass

    def _close_single_dm(self, channel_id, username, row=None):
        if row:
            row.configure(fg_color="#202225")
        def worker():
            try:
                self.api.close_dm(channel_id)
                self.after(0, self._on_single_dm_closed, channel_id)
            except Exception:
                if row:
                    self.after(0, lambda: row.configure(fg_color=CARD))
        threading.Thread(target=worker, daemon=True).start()

    def _on_single_dm_closed(self, channel_id):
        self.stale_dms = [d for d in self.stale_dms if d["channel_id"] != channel_id]
        self.selected_ids.discard(channel_id)
        self._update_filter_counts()
        self._render_items()

    def _confirm_delete_single_friend(self, uid, username):
        dlg = ConfirmDialog(
            self, "Confirm Removal",
            f"Remove @{username} from friends? This cannot be undone.",
            btn_text="Remove"
        )
        self.wait_window(dlg)
        if not dlg.result:
            return
        def worker():
            try:
                self.api.delete_friend(uid)
                self.after(0, self._on_single_friend_deleted, uid)
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _on_single_friend_deleted(self, uid):
        self.friends_data = [f for f in self.friends_data if f["user"]["id"] != uid]
        self.selected_ids.discard(uid)
        self._update_filter_counts()
        self._render_items()

    def _toggle(self, item_id, checked):
        if checked:
            self.selected_ids.add(item_id)
        else:
            self.selected_ids.discard(item_id)
        self._update_count()

    def _select_all(self):
        for item in self._filtered_items():
            item_id = item["channel_id"] if self.current_filter == "stale_dms" else item["user"]["id"]
            self.selected_ids.add(item_id)
            if item_id in self.card_widgets:
                self.card_widgets[item_id]["var"].set(True)
        self._update_count()

    def _deselect_all(self):
        for item_id in list(self.selected_ids):
            if item_id in self.card_widgets:
                self.card_widgets[item_id]["var"].set(False)
        self.selected_ids.clear()
        self._update_count()

    def _update_count(self):
        n = len(self.selected_ids)
        self.sel_label.configure(text=f"{n} selected", text_color=DANGER if n else TEXT_MUTED)
        if self.current_filter == "stale_dms":
            action_text = f"Close {n} DM{'s' if n != 1 else ''}" if n else "Close Selected DMs"
        else:
            action_text = f"Remove {n} Friend{'s' if n != 1 else ''}" if n else "Remove Selected"
        self.del_btn.configure(
            state="normal" if n else "disabled",
            text=action_text,
        )

    def _on_delete(self):
        n = len(self.selected_ids)
        if not n:
            return

        if self.current_filter == "stale_dms":
            dlg = ConfirmDialog(
                self, "Confirm Close DMs",
                f"Close {n} DM channel{'s' if n != 1 else ''}? They will be removed from your sidebar.",
                btn_text="Close DMs"
            )
            self.wait_window(dlg)
            if not dlg.result:
                return
            targets = [
                (d["channel_id"], d["user"].get("username", ""))
                for d in self.stale_dms if d["channel_id"] in self.selected_ids
            ]
            progress = ProgressDialog(self, len(targets), title="Closing DMs", action_word="closed")
            threading.Thread(target=self._close_dm_worker, args=(targets, progress), daemon=True).start()
        else:
            dlg = ConfirmDialog(
                self, "Confirm Removal",
                f"Remove {n} friend{'s' if n != 1 else ''}? This cannot be undone.",
                btn_text="Remove"
            )
            self.wait_window(dlg)
            if not dlg.result:
                return
            targets = [
                (f["user"]["id"], f["user"].get("username", ""))
                for f in self.friends_data if f["user"]["id"] in self.selected_ids
            ]
            progress = ProgressDialog(self, len(targets), title="Removing Friends", action_word="removed")
            threading.Thread(target=self._delete_worker, args=(targets, progress), daemon=True).start()

    def _delete_worker(self, targets, progress):
        removed = []
        for i, (uid, name) in enumerate(targets, 1):
            if progress.cancelled:
                break
            try:
                self.api.delete_friend(uid)
                removed.append(uid)
                self.after(0, progress.update_progress, i, name)
            except Exception:
                self.after(0, progress.update_progress, i, f"{name} (failed)")
            if i < len(targets):
                time.sleep(1.5)
        self.after(0, self._delete_done, removed, progress)

    def _delete_done(self, removed, progress):
        self.friends_data = [f for f in self.friends_data if f["user"]["id"] not in removed]
        self.selected_ids -= set(removed)
        self._update_filter_counts()
        try:
            if not progress.cancelled:
                progress.mark_complete()
        except Exception:
            pass
        self._render_items()

    def _close_dm_worker(self, targets, progress):
        closed = []
        for i, (cid, name) in enumerate(targets, 1):
            if progress.cancelled:
                break
            try:
                self.api.close_dm(cid)
                closed.append(cid)
                self.after(0, progress.update_progress, i, name)
            except Exception:
                self.after(0, progress.update_progress, i, f"{name} (failed)")
            if i < len(targets):
                time.sleep(1.0)
        self.after(0, self._close_dm_done, closed, progress)

    def _close_dm_done(self, closed, progress):
        self.stale_dms = [d for d in self.stale_dms if d["channel_id"] not in closed]
        self.selected_ids -= set(closed)
        self._update_filter_counts()
        try:
            if not progress.cancelled:
                progress.mark_complete()
        except Exception:
            pass
        self._render_items()
