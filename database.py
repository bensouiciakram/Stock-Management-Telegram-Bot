import aiosqlite

DB_NAME = "clients.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Create clients table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                credit REAL DEFAULT 0
            )
        """)

        # Create admins table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # Create nuts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS nuts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                packages INTEGER DEFAULT 0
            )
        """)

        # Create requests table (references both client and admin)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                nut_id INTEGER NOT NULL,
                packages INTEGER NOT NULL,
                credit_paid REAL DEFAULT 0,
                description TEXT,
                FOREIGN KEY (admin_id) REFERENCES admins(id),
                FOREIGN KEY (nut_id) REFERENCES nuts(id)
            )
        """)


        await db.commit()

async def add_client(name:str,credit:int=0):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO clients (name,credit) VALUES (?,?)", (name,credit))
        await db.commit()

async def get_clients():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, credit FROM clients")
        return await cursor.fetchall()

async def update_credit(client_id:int, amount:int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE clients SET credit = credit + ? WHERE id = ?", (amount, client_id))
        await db.commit()

async def get_client_by_name(name:str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, credit FROM clients WHERE name=?", (name,))
        return await cursor.fetchone()
    
# ---------- ADMIN HELPERS (add to database.py) ----------
async def add_admin(name: str):
    """Create an admin entry (predefine admins manually or via a setup script)."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (name) VALUES (?)",
            (name,)
        )
        await db.commit()

async def get_admin_by_name(name: str):
    """Return (id, name) for an admin, or None if not found."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name FROM admins WHERE name = ?", (name,))
        return await cursor.fetchone()

async def get_admins():
    """Return list of (id, name) for all admins."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name FROM admins")
        return await cursor.fetchall()

# ---------- NUTS OPERATIONS ----------
async def add_nut(name: str, packages: int = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO nuts (name, packages) VALUES (?, ?)",
            (name, packages)
        )
        await db.commit()


async def get_nuts():
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, packages FROM nuts")
        return await cursor.fetchall()


async def get_nut_by_name(name: str):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT id, name, packages FROM nuts WHERE name = ?", (name,))
        return await cursor.fetchone()


async def update_packages(nut_id: int, delta: int):
    """Increase or decrease the number of packages for a nut."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE nuts SET packages = packages + ? WHERE id = ?",
            (delta, nut_id)
        )
        await db.commit()


# ---------- REQUESTS OPERATIONS ----------
async def add_request(admin_id: int, nut_id: int, packages: int, credit_paid: float, description: str = ""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            """
            INSERT INTO requests (admin_id, nut_id, packages, credit_paid, description)
            VALUES (?, ?, ?, ?, ?)
            """,
            (admin_id, nut_id, packages, credit_paid, description)
        )
        await db.commit()


async def get_requests():
    """Return all requests with related admin and nut names."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT r.id, a.name AS admin, n.name AS nut, r.packages, r.credit_paid, r.description
            FROM requests r
            JOIN admins a ON r.admin_id = a.id
            JOIN nuts n ON r.nut_id = n.id
        """)
        return await cursor.fetchall()
