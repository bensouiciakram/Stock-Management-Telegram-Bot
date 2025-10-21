from abc import abstractmethod
import aiosqlite

DB_NAME = "nuts.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Create clients table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS client (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                credit REAL DEFAULT 0
            )
        """)

        # Create admins table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)

        # Create nuts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS nut (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                packages INTEGER DEFAULT 0
            )
        """)

        # Create requests table (references both client and admin)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS request (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                nut_id INTEGER NOT NULL,
                packages INTEGER NOT NULL,
                credit_paid REAL DEFAULT 0,
                description TEXT,
                requester_id INTEGER,
                approved INTEGER DEFAULT 0,
                FOREIGN KEY (admin_id) REFERENCES admin(id),
                FOREIGN KEY (nut_id) REFERENCES nut(id)
            )
        """)
        await db.commit()

class BaseDbService :
    def __init__(self,table_name:str):
        self.table_name = table_name

    def get_add_query(self,**kwargs) -> str :
        keys = kwargs.keys()
        keys_length = len(keys)
        return f"INSERT OR IGNORE INTO {self.table_name} ({','.join(keys)}) VALUES ({','.join('?'*keys_length)})"

    async def add(self,**kwargs):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(
                self.get_add_query(**kwargs),
                list(kwargs.values())
            )
            await db.commit()
            return cursor.lastrowid

    async def list(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(f"SELECT * FROM {self.table_name}")
            return await cursor.fetchall()
        
    async def get(self,name:str):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(f"SELECT * FROM {self.table_name} WHERE name=?", (name,))
            return await cursor.fetchone()

    async def get_by_id(self, row_id: int):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(f"SELECT * FROM {self.table_name} WHERE id=?", (row_id,))
            return await cursor.fetchone()

    async def update_by_id(self, row_id: int, **kwargs):
        async with aiosqlite.connect(DB_NAME) as db:
            sets = ",".join([f"{k}=?" for k in kwargs.keys()])
            await db.execute(f"UPDATE {self.table_name} SET {sets} WHERE id=?", [*kwargs.values(), row_id])
            await db.commit()