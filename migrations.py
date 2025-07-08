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
            email_server TEXT,
            email_port INTEGER,
            email_username TEXT,
            email_password TEXT,
            email_from TEXT,
            email_subject TEXT,
            email_message TEXT
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
            email_to TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )