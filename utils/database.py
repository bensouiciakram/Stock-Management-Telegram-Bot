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
            await db.execute(
                self.get_add_query(**kwargs),
                list(kwargs.values())
            )
            await db.commit()

    async def list(self):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(f"SELECT * FROM {self.table_name}")
            return await cursor.fetchall()
        
    async def get(self,name:str):
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(f"SELECT * FROM {self.table_name} WHERE name=?", (name,))
            return await cursor.fetchone()
        

class ClientDbService(BaseDbService):

    def __init__(self,table_name:str):
        super().__init__(table_name=table_name)

    async def update(self,client_id:int,amount:int):
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE clients SET credit = credit + ? WHERE id = ?", (amount, client_id))
            await db.commit()
        

class NutDbService(BaseDbService):


    def __init__(self,table_name:str):
        super().__init__(table_name=table_name)

    async def update(self,nut_id: int, delta: int):
        """Increase or decrease the number of packages for a nut."""
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute(
                "UPDATE nuts SET packages = packages + ? WHERE id = ?",
                (delta, nut_id)
            )
            await db.commit()



class RequestDbService(BaseDbService):


    def __init__(self,table_name:str):
        super().__init__(table_name=table_name)

    async def list():
        """Return all requests with related admin and nut names."""
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
                SELECT r.id, a.name AS admin, n.name AS nut, r.packages, r.credit_paid, r.description
                FROM requests r
                JOIN admins a ON r.admin_id = a.id
                JOIN nuts n ON r.nut_id = n.id
            """)
            return await cursor.fetchall()

