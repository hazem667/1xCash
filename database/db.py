import aiosqlite
import os

DB_PATH = "data/bot.db"

# إنشاء مجلد data تلقائياً لو مش موجود
os.makedirs("data", exist_ok=True)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # جدول المستخدمين
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                joined_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # جدول الأدمنز
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                added_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # جدول طلبات الإيداع
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

        # جدول طلبات السحب
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

        # جدول الرسائل القابلة للتعديل
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # جدول الإعدادات
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # جدول المحادثات المباشرة
        await db.execute("""
            CREATE TABLE IF NOT EXISTS live_chats (
                user_id INTEGER PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                chat_type TEXT DEFAULT 'support',
                order_id INTEGER,
                started_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # جدول السجلات
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

        await db.commit()

    # إدراج القيم الافتراضية
    await insert_defaults()


async def insert_defaults():
    async with aiosqlite.connect(DB_PATH) as db:
        # الرسائل الافتراضية
        default_messages = {
            "welcome": (
                "💙 مرحبًا بك في 1Cash\n\n"
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
            "deposit_ask_photo": (
                "📸 أرسل صورة إيصال التحويل:"
            ),
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
                "أول إيداع (160 جنيه أو أكثر)\n"
                "✅ احصل على 100% بونص إضافي (ضعف قيمة الإيداع) + 30 لفة مجانية على لعبة Reliquary of Ra\n\n"
                "الإيداع الثاني\n"
                "✅ 125% بونص + 45 لفة مجانية على لعبة Voltage Cash\n\n"
                "الإيداع الثالث\n"
                "✅ 150% بونص + 60 لفة مجانية على لعبة Juicy Fruits 27 Ways\n\n"
                "الإيداع الرابع\n"
                "✅ 200% بونص + 75 لفة مجانية على لعبة Rich of the Mermaid Hold and Spin\n\n"
                "📌 مهم: للاستفادة من جميع المكافآت والعروض، يجب:\n"
                "• التسجيل باستخدام البروموكود MZN100\n"
                "• استكمال بيانات الملف الشخصي\n\n"
                "✨ استمتع بالعروض الترحيبية واستفد من جميع المكافآت المتاحة للمستخدمين الجدد.\n\n"
                "🎟 Promo Code: MZN100"
            ),
        }

        default_settings = {
            "deposit_enabled": "1",
            "withdraw_enabled": "1",
            "promo_enabled": "1",
            "maintenance_mode": "0",
            "support_username": "z7yzf",
            "bot_name": "1Cash",
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

        await db.commit()


# ── Helpers ──────────────────────────────────────────────

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
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
            (user_id, username or "")
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


async def create_deposit_order(user_id, username, account_id, phone, photo_file_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO deposit_orders
               (user_id, username, account_id, phone, photo_file_id)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username or "", account_id, phone, photo_file_id)
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
