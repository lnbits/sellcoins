async def m001_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
        """
        CREATE TABLE sellcoins.settings (
            id TEXT PRIMARY KEY NOT NULL,
            denomination TEXT NOT NULL,
            send_wallet_id TEXT NOT NULL,
            receive_wallet_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            header_image TEXT NOT NULL,
            haircut INTEGER,
            auto_convert BOOLEAN,
            email BOOLEAN,
            nostr BOOLEAN,
            launch_page BOOLEAN,
            message TEXT
        );
    """
    )


async def m002_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
        """
        CREATE TABLE sellcoins.products (
            id TEXT PRIMARY KEY NOT NULL,
            settings_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            amount INTEGER,
            price INTEGER
        );
    """
    )


async def m003_initial(db):
    """
    Initial templates table.
    """
    await db.execute(
       f"""
        CREATE TABLE sellcoins.orders (
            id TEXT PRIMARY KEY NOT NULL,
            product_id TEXT NOT NULL,
            settings_id TEXT NOT NULL,
            email_to TEXT,
            nostr_key TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )

async def m004_add_order_payment_details(db):
    await db.execute("ALTER TABLE sellcoins.orders ADD COLUMN payment_request TEXT")
    await db.execute("ALTER TABLE sellcoins.orders ADD COLUMN payment_hash TEXT")

async def m005_add_settings_testing_mode(db):
    await db.execute("ALTER TABLE sellcoins.settings ADD COLUMN live_mode BOOLEAN")

async def m005_add_order_sats_amount(db):
    await db.execute("ALTER TABLE sellcoins.orders ADD COLUMN sats_amount INTEGER")
