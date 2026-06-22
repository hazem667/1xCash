import aiosqlite
import os
import json

DB_PATH = "data/bot.db"

os.makedirs("data", exist_ok=True)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deposit_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                responses TEXT,
                amount TEXT,
                photo_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                responses TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS live_chats (
                user_id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                chat_type TEXT DEFAULT 'support',
                order_id INTEGER,
                started_at TEXT DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                admin_id INTEGER,
                target_id INTEGER,
                details TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # جدول خطوات الإيداع الديناميكية
        await db.execute("""
            CREATE TABLE IF NOT EXISTS flow_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                flow_type TEXT,
                step_order INTEGER,
                label TEXT,
                question TEXT,
                answer_type TEXT DEFAULT 'text',
                validation TEXT,
                options TEXT,
                is_photo INTEGER DEFAULT 0,
                is_info_message INTEGER DEFAULT 0,
                info_text TEXT
            )
        """)
        # جدول أزرار الكيبورد الرئيسية الديناميكية
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT,
                button_type TEXT DEFAULT 'link',
                url TEXT,
                position INTEGER DEFAULT 0,
                visible INTEGER DEFAULT 1
            )
        """)
        # جدول أسماء الأزرار الثابتة
        await db.execute("""
            CREATE TABLE IF NOT EXISTS button_labels (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()

    await insert_defaults()


async def insert_defaults():
    async with aiosqlite.connect(DB_PATH) as db:
        default_messages = {
            "welcome": (
                "💙 مرحبًا بك في 1xCash\n\n"
                "الوكيل المعتمد لدى منصة ...\n"
                "لإجراء عمليات سحب وإيداع سلسة وآمنة 100% على مدار 24/7.\n\n"
                "يمكنك استخدام الأزرار بالأسفل لإجراء عمليات الإيداع أو السحب بسهولة.\n\n"
                "في حال واجهتك أي مشكلة، تواصل مع الإدارة: @z7yzf"
            ),
            "deposit_intro": (
                "💵 *طلب إيداع*\n\n"
                "سيتم إرسال طلبك للإدارة للمراجعة.\n"
                "اضغط متابعة للبدء."
            ),
            "withdraw_intro": (
                "💸 *طلب سحب*\n\n"
                "اضغط متابعة للبدء."
            ),
            "deposit_sent": (
                "⏳ تم إرسال طلب الإيداع بنجاح!\n"
                "سيتم مراجعته من قبل الإدارة والرد عليك في أقرب وقت."
            ),
            "deposit_accepted": (
                "✅ تم قبول طلب الإيداع الخاص بك بنجاح.\n\n"
                "💰 تم إضافة رصيد بقيمة: {amount} جنيه مصري\n"
                "🕒 التاريخ: {date}\n"
                "⏰ الوقت: {time}\n\n"
                "نشكر ثقتك بنا 💙"
            ),
            "deposit_rejected": (
                "❌ عذرًا، تم رفض طلب الإيداع الخاص بك.\n\n"
                "🕒 التاريخ: {date}\n\n"
                "للاستفسار تواصل مع الإدارة: @z7yzf"
            ),
            "withdraw_sent": (
                "⏳ تم استلام طلب السحب بنجاح!\n"
                "سيتم مراجعته من قبل الإدارة والرد عليك في أقرب وقت."
            ),
            "withdraw_success": (
                "✅ تمت عملية السحب بنجاح!\n\n"
                "🕒 التاريخ: {date}\n"
                "⏰ الوقت: {time}\n\n"
                "نشكر ثقتك بنا 💙"
            ),
            "withdraw_rejected": (
                "❌ عذرًا، تم رفض طلب السحب الخاص بك.\n\n"
                "🕒 التاريخ: {date}\n\n"
                "للاستفسار تواصل مع الإدارة: @z7yzf"
            ),
            "help_requested": (
                "🆘 تم إرسال طلب المساعدة للإدارة.\n"
                "برجاء الانتظار لحظات، سيتم التواصل معك قريبًا."
            ),
            "admin_connected": (
                "👨‍💻 الإدارة متصلة معك الآن.\n"
                "يمكنك إرسال رسالتك وسيتم الرد مباشرة."
            ),
            "promo": (
                "🎟 سجّل الآن باستخدام البروموكود: *MZN100*\n\n"
                "مكافآت حصرية للمستخدمين الجدد عند التسجيل بالبروموكود.\n\n"
                "🎟 Promo Code: MZN100"
            ),
            "transfer_info": (
                "قم بتحويل المبلغ المطلوب إلى الرقم التالي:\n"
                "01156802514\n\n"
                "عن طريق:\n"
                "Instapay (تحويل من Instapay إلى المحفظة)\n"
                "Vodafone Cash\n"
                "Etisalat Cash\n\n"
                "⚠️ ملحوظة:\n"
                "الحد الأدنى للإيداع: 10 جنيه مصري\n\n"
                "بعد إتمام التحويل، يرجى إرسال صورة التحويل والرقم المحوّل منه ثم اضغط إرسال لإكمال طلب الإيداع، أو اضغط إلغاء لإعادة طلب الإيداع."
            ),
        }

        default_settings = {
            "deposit_enabled": "1",
            "withdraw_enabled": "1",
            "promo_enabled": "1",
            "maintenance_mode": "0",
            "support_username": "z7yzf",
            "bot_name": "1xCash",
            "soon_url": "",
        }

        default_button_labels = {
            "deposit": "💵 إيداع",
            "withdraw": "💸 سحب",
            "promo": "🎟 برومو كود",
            "soon": "🔜 Soon",
        }

        for key, value in default_messages.items():
            await db.execute(
                "INSERT OR IGNORE INTO messages (key, value) VALUES (?, ?)",
                (key, value)
            )
        for key, value in default_settings.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
        for key, value in default_button_labels.items():
            await db.execute(
                "INSERT OR IGNORE INTO button_labels (key, value) VALUES (?, ?)",
                (key, value)
            )

        # خطوات الإيداع الافتراضية
        existing = await db.execute("SELECT COUNT(*) FROM flow_steps WHERE flow_type='deposit'")
        count = (await existing.fetchone())[0]
        if count == 0:
            deposit_steps = [
                (1, "account_id", "💠 أدخل ID حسابك في المنصة:", "text", "digits", None, 0, 0, None),
                (2, "amount", "💰 أدخل المبلغ المراد إيداعه:", "text", "digits", None, 0, 0, None),
                (3, "transfer_info", "", "info", None, None, 0, 1, None),
                (4, "photo", "📸 أرسل صورة إيصال التحويل:", "photo", None, None, 1, 0, None),
                (5, "phone", "📱 أدخل الرقم المحوّل منه:", "text", "any", None, 0, 0, None),
            ]
            for s in deposit_steps:
                await db.execute(
                    "INSERT INTO flow_steps (flow_type, step_order, label, question, answer_type, validation, options, is_photo, is_info_message, info_text) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    ("deposit", s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8])
                )

        existing2 = await db.execute("SELECT COUNT(*) FROM flow_steps WHERE flow_type='withdraw'")
        count2 = (await existing2.fetchone())[0]
        if count2 == 0:
            withdraw_steps = [
                (1, "account_id", "💠 أدخل ID حسابك في المنصة:", "text", "digits", None, 0, 0, None),
                (2, "code_wait", "🔑 اطلب كود السحب من المنصة الآن ثم اضغط *تم* عندما تحصل عليه.\n\nأو اضغط *🆘 طلب مساعدة* إذا واجهتك مشكلة.", "code_wait", None, None, 0, 0, None),
                (3, "code", "🔑 أدخل كود السحب:", "text", "any", None, 0, 0, None),
                (4, "amount", "💰 أدخل مبلغ السحب:", "text", "digits", None, 0, 0, None),
                (5, "method", "💳 أدخل طريقة الاستلام:\nمثال: Vodafone Cash / Etisalat Cash / InstaPay", "text", "any", None, 0, 0, None),
            ]
            for s in withdraw_steps:
                await db.execute(
                    "INSERT INTO flow_steps (flow_type, step_order, label, question, answer_type, validation, options, is_photo, is_info_message, info_text) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    ("withdraw", s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8])
                )

        await db.commit()


# ── Flow Steps ───────────────────────────────────────────

async def get_flow_steps(flow_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, step_order, label, question, answer_type, validation, options, is_photo, is_info_message, info_text FROM flow_steps WHERE flow_type=? ORDER BY step_order",
            (flow_type,)
        ) as cur:
            return await cur.fetchall()


async def add_flow_step(flow_type, step_order, label, question, answer_type, validation, is_photo, is_info_message, info_text):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO flow_steps (flow_type, step_order, label, question, answer_type, validation, is_photo, is_info_message, info_text) VALUES (?,?,?,?,?,?,?,?,?)",
            (flow_type, step_order, label, question, answer_type, validation, is_photo, is_info_message, info_text)
        )
        await db.commit()


async def delete_flow_step(step_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM flow_steps WHERE id=?", (step_id,))
        await db.commit()


async def update_flow_step_question(step_id: int, question: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE flow_steps SET question=? WHERE id=?", (question, step_id))
        await db.commit()


# ── Button Labels ────────────────────────────────────────

async def get_button_label(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM button_labels WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            defaults = {
                "deposit": "💵 إيداع", "withdraw": "💸 سحب",
                "promo": "🎟 برومو كود", "soon": "🔜 Soon"
            }
            return row[0] if row else defaults.get(key, key)


async def set_button_label(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO button_labels (key, value) VALUES (?, ?)", (key, value))
        await db.commit()


# ── Custom Buttons ───────────────────────────────────────

async def get_custom_buttons():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, label, button_type, url, position FROM custom_buttons WHERE visible=1 ORDER BY position") as cur:
            return await cur.fetchall()


async def add_custom_button(label, url, position=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO custom_buttons (label, button_type, url, position) VALUES (?, 'link', ?, ?)",
            (label, url, position)
        )
        await db.commit()


async def delete_custom_button(btn_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM custom_buttons WHERE id=?", (btn_id,))
        await db.commit()


# ── Helpers ──────────────────────────────────────────────

async def get_message(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM messages WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else f"[{key}]"


async def set_message(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO messages (key, value) VALUES (?, ?)", (key, value))
        await db.commit()


async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        await db.commit()


async def register_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username or "", full_name or "")
        )
        await db.commit()


async def is_admin(user_id: int) -> bool:
    admin_id = int(os.getenv("ADMIN_ID", "0"))
    if user_id == admin_id:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def get_all_admins():
    admin_id = int(os.getenv("ADMIN_ID", "0"))
    admins = [admin_id]
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM admins") as cur:
            rows = await cur.fetchall()
            for row in rows:
                if row[0] not in admins:
                    admins.append(row[0])
    return admins


async def add_admin(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)", (user_id, username or ""))
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


async def create_deposit_order(user_id, username, responses: dict, photo_file_id=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO deposit_orders (user_id, username, responses, photo_file_id) VALUES (?, ?, ?, ?)",
            (user_id, username or "", json.dumps(responses, ensure_ascii=False), photo_file_id)
        )
        await db.commit()
        return cur.lastrowid


async def create_withdraw_order(user_id, username, responses: dict):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO withdraw_orders (user_id, username, responses) VALUES (?, ?, ?)",
            (user_id, username or "", json.dumps(responses, ensure_ascii=False))
        )
        await db.commit()
        return cur.lastrowid


async def get_deposit_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM deposit_orders WHERE id=?", (order_id,)) as cur:
            return await cur.fetchone()


async def get_withdraw_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM withdraw_orders WHERE id=?", (order_id,)) as cur:
            return await cur.fetchone()


async def update_deposit_status(order_id: int, status: str, amount: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if amount:
            await db.execute(
                "UPDATE deposit_orders SET status=?, amount=?, updated_at=datetime('now') WHERE id=?",
                (status, amount, order_id)
            )
        else:
            await db.execute(
                "UPDATE deposit_orders SET status=?, updated_at=datetime('now') WHERE id=?",
                (status, order_id)
            )
        await db.commit()


async def update_withdraw_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE withdraw_orders SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, order_id)
        )
        await db.commit()


async def get_live_chat(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM live_chats WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()


async def set_live_chat(user_id: int, status: str, chat_type: str = "support", order_id: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO live_chats (user_id, status, chat_type, order_id) VALUES (?, ?, ?, ?)",
            (user_id, status, chat_type, order_id)
        )
        await db.commit()


async def delete_live_chat(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM live_chats WHERE user_id=?", (user_id,))
        await db.commit()


async def get_active_chats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM live_chats WHERE status='active'") as cur:
            return await cur.fetchall()


async def get_pending_chats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM live_chats WHERE status='pending'") as cur:
            return await cur.fetchall()


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM deposit_orders WHERE status='pending'") as cur:
            dep_pending = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM deposit_orders WHERE status='accepted'") as cur:
            dep_accepted = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM withdraw_orders WHERE status='pending'") as cur:
            wit_pending = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM withdraw_orders WHERE status='accepted'") as cur:
            wit_accepted = (await cur.fetchone())[0]
    return {
        "users": users, "dep_pending": dep_pending,
        "dep_accepted": dep_accepted, "wit_pending": wit_pending,
        "wit_accepted": wit_accepted,
    }


async def log_action(action: str, admin_id: int, target_id: int = None, details: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (action, admin_id, target_id, details) VALUES (?, ?, ?, ?)",
            (action, admin_id, target_id, details)
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            return [row[0] for row in await cur.fetchall()]
