import aiosqlite
import os

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
                account_id TEXT,
                phone TEXT,
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
                account_id TEXT,
                code TEXT,
                amount TEXT,
                method TEXT,
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
        # جدول أسماء الأزرار الثابتة القابلة للتغيير
        await db.execute("""
            CREATE TABLE IF NOT EXISTS button_labels (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        # جدول الأزرار المخصصة (لينكات)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT,
                url TEXT,
                position INTEGER DEFAULT 0
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
            "deposit_ask_id": "💠 أدخل ID حسابك في المنصة:",
            "deposit_ask_amount": "💰 أدخل المبلغ الذي ستحوله:",
            "deposit_transfer_info": (
                "قم بتحويل المبلغ إلى الرقم التالي:\n"
                "01156802514\n\n"
                "عن طريق:\n"
                "Instapay / Vodafone Cash / Etisalat Cash\n\n"
                "⚠️ الحد الأدنى للإيداع: 10 جنيه\n\n"
                "بعد التحويل أرسل صورة الإيصال ثم اضغط إرسال."
            ),
            "deposit_ask_photo": "📸 أرسل صورة إيصال التحويل:",
            "deposit_ask_phone": "📱 أدخل الرقم المحوّل منه:",
            "deposit_sent": (
                "⏳ تم إرسال طلب الإيداع بنجاح!\n"
                "سيتم مراجعته من قبل الإدارة والرد عليك في أقرب وقت."
            ),
            "deposit_accepted": (
                "✅ تم قبول طلب الإيداع الخاص بك بنجاح.\n\n"
                "💠 ID الحساب: {account_id}\n"
                "💰 تم إضافة رصيد بقيمة: {amount} جنيه مصري\n"
                "🕒 التاريخ: {date}\n"
                "⏰ الوقت: {time}\n\n"
                "نشكر ثقتك بنا 💙"
            ),
            "deposit_rejected": (
                "❌ عذرًا، تم رفض طلب الإيداع الخاص بك.\n\n"
                "💠 ID الحساب: {account_id}\n"
                "🕒 التاريخ: {date}\n\n"
                "للاستفسار تواصل مع الإدارة: @z7yzf"
            ),
            "withdraw_intro": (
                "💸 *طلب سحب*\n\n"
                "اضغط متابعة للبدء."
            ),
            "withdraw_ask_id": "💠 أدخل ID حسابك في المنصة:",
            "withdraw_ask_code": (
                "🔑 اطلب كود السحب من المنصة الآن، ثم اضغط *تم* عندما تحصل عليه.\n\n"
                "أو اضغط *🆘 طلب مساعدة* إذا واجهتك مشكلة."
            ),
            "withdraw_ask_code_value": "🔑 أدخل كود السحب:",
            "withdraw_ask_amount": "💰 أدخل مبلغ السحب:",
            "withdraw_ask_method": (
                "💳 أدخل طريقة الاستلام:\n"
                "مثال: Vodafone Cash / Etisalat Cash / InstaPay"
            ),
            "withdraw_sent": (
                "⏳ تم استلام طلب السحب بنجاح!\n"
                "سيتم مراجعته من قبل الإدارة والرد عليك في أقرب وقت."
            ),
            "withdraw_success": (
                "✅ تمت عملية السحب بنجاح!\n\n"
                "💠 ID الحساب: {account_id}\n"
                "💰 المبلغ: {amount} جنيه مصري\n"
                "💳 الطريقة: {method}\n"
                "🕒 التاريخ: {date}\n"
                "⏰ الوقت: {time}\n\n"
                "نشكر ثقتك بنا 💙"
            ),
            "withdraw_rejected": (
                "❌ عذرًا، تم رفض طلب السحب الخاص بك.\n\n"
                "💠 ID الحساب: {account_id}\n"
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

        # أسماء الأزرار الافتراضية
        default_labels = {
            "deposit": "💵 إيداع",
            "withdraw": "💸 سحب",
            "promo": "🎟 برومو كود",
            "soon": "🔜 قريبًا",
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
        for key, value in default_labels.items():
            await db.execute(
                "INSERT OR IGNORE INTO button_labels (key, value) VALUES (?, ?)",
                (key, value)
            )
        await db.commit()


# ── Button Labels ──────────────────────────────────────────

async def get_button_label(key: str) -> str:
    defaults = {
        "deposit": "💵 إيداع",
        "withdraw": "💸 سحب",
        "promo": "🎟 برومو كود",
        "soon": "🔜 قريبًا",
    }
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM button_labels WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else defaults.get(key, key)


async def set_button_label(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO button_labels (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


# ── Custom Buttons ─────────────────────────────────────────

async def get_custom_buttons():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, label, url, position FROM custom_buttons ORDER BY position, id"
        ) as cur:
            return await cur.fetchall()


async def add_custom_button(label: str, url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO custom_buttons (label, url) VALUES (?, ?)",
            (label, url)
        )
        await db.commit()


async def delete_custom_button(btn_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM custom_buttons WHERE id=?", (btn_id,))
        await db.commit()


# ── Helpers ────────────────────────────────────────────────

async def get_message(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM messages WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else f"[{key}]"


async def set_message(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO messages (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        await db.commit()


async def register_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username or "", full_name or "")
        )
        await db.commit()


async def is_admin(user_id: int) -> bool:
    admin_id_env = os.getenv("ADMIN_ID", "0")
    try:
        admin_id = int(admin_id_env)
    except ValueError:
        admin_id = 0
    if admin_id != 0 and user_id == admin_id:
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def get_all_admins():
    admin_id_env = os.getenv("ADMIN_ID", "0")
    try:
        admin_id = int(admin_id_env)
    except ValueError:
        admin_id = 0
    admins = []
    if admin_id != 0:
        admins.append(admin_id)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM admins") as cur:
            rows = await cur.fetchall()
            for row in rows:
                if row[0] not in admins:
                    admins.append(row[0])
    return admins


async def add_admin(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
            (user_id, username or "")
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


async def create_deposit_order(user_id, username, account_id, amount, phone, photo_file_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO deposit_orders
               (user_id, username, account_id, amount, phone, photo_file_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username or "", account_id, amount, phone, photo_file_id)
        )
        await db.commit()
        return cur.lastrowid


async def create_withdraw_order(user_id, username, account_id, code, amount, method):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO withdraw_orders
               (user_id, username, account_id, code, amount, method)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, username or "", account_id, code, amount, method)
        )
        await db.commit()
        return cur.lastrowid


async def get_deposit_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM deposit_orders WHERE id=?", (order_id,)
        ) as cur:
            return await cur.fetchone()


async def get_withdraw_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM withdraw_orders WHERE id=?", (order_id,)
        ) as cur:
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
        async with db.execute(
            "SELECT * FROM live_chats WHERE user_id=?", (user_id,)
        ) as cur:
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
        async with db.execute(
            "SELECT * FROM live_chats WHERE status='active'"
        ) as cur:
            return await cur.fetchall()


async def get_pending_chats():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM live_chats WHERE status='pending'"
        ) as cur:
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
        "users": users,
        "dep_pending": dep_pending,
        "dep_accepted": dep_accepted,
        "wit_pending": wit_pending,
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
