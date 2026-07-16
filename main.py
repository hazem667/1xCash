import asyncio
import logging
import os
from telegram.ext import Application, MessageHandler, filters

from database.db import init_db
from handlers import (
    user_menu, deposit, withdraw, support,
    myops, order_actions, admin_panel
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def post_init(app):
    await init_db()
    logger.info("✅ قاعدة البيانات جاهزة")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN غير موجود في متغيرات البيئة!")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # ── الترتيب مهم جداً ──────────────────────────────

    # 1. Admin conversations first (highest priority)
    for h in admin_panel.get_handlers():
        app.add_handler(h, group=0)

    # 2. Order action callbacks (accept/skip/done/reject/relay)
    for h in order_actions.get_handlers():
        app.add_handler(h, group=1)

    # 3. User conversations
    app.add_handler(deposit.get_handler(), group=2)
    app.add_handler(withdraw.get_handler(), group=2)
    app.add_handler(support.get_handler(), group=2)

    # 4. My operations
    for h in myops.get_handlers():
        app.add_handler(h, group=3)

    # 5. User menu (/start + static buttons)
    for h in user_menu.get_handlers():
        app.add_handler(h, group=4)

    # 6. Catch-all for proofs / tote / custom buttons
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _catch_all),
        group=5
    )

    logger.info("✅ البوت شغال...")
    app.run_polling(drop_pending_updates=True)


async def _catch_all(update, ctx):
    from handlers.user_menu import handle_proofs, handle_tote, handle_custom_buttons
    await handle_proofs(update, ctx)
    await handle_tote(update, ctx)
    await handle_custom_buttons(update, ctx)


if __name__ == "__main__":
    main()
