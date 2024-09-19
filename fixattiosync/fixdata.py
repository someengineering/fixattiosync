import os
import psycopg
from psycopg.rows import dict_row
from uuid import UUID
from argparse import ArgumentParser
from .logger import log
from .fixresources import FixUser, FixWorkspace
from typing import Optional


class FixData:
    def __init__(self, db: str, user: str, password: str, host: str = "localhost", port: int = 5432) -> None:
        self.db = db
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.conn: Optional[psycopg.Connection] = None
        self.hydrated = False
        self.__workspaces: dict[UUID, FixWorkspace] = {}
        self.__users: dict[UUID, FixUser] = {}

    @property
    def users(self) -> list[FixUser]:
        if not self.hydrated:
            self.hydrate()
        return list(self.__users.values())

    @property
    def workspaces(self) -> list[FixWorkspace]:
        if not self.hydrated:
            self.hydrate()
        return list(self.__workspaces.values())

    def connect(self) -> None:
        log.debug("Connecting to the database")
        if self.conn is None:
            try:
                self.conn = psycopg.connect(
                    dbname=self.db, user=self.user, password=self.password, host=self.host, port=self.port
                )
                log.debug("Connection successful")
            except psycopg.DatabaseError as e:
                log.error(f"Error connecting to the database: {e}")
                self.conn = None

    def hydrate(self) -> None:
        if self.conn is None:
            self.connect()

        log.debug("Hydrating Fix database data")
        if self.conn is not None:
            try:
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."user";')
                    rows = cursor.fetchall()
                    for row in rows:
                        user = FixUser(**row)
                        self.__users[user.id] = user
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."organization";')
                    rows = cursor.fetchall()
                    for row in rows:
                        workspace = FixWorkspace(**row)
                        self.__workspaces[workspace.id] = workspace
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."organization_owners";')
                    rows = cursor.fetchall()
                    for row in rows:
                        self.__workspaces[row["organization_id"]].owner = self.__users[row["user_id"]]
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."organization_members";')
                    rows = cursor.fetchall()
                    for row in rows:
                        self.__workspaces[row["organization_id"]].users.append(self.__users[row["user_id"]])
                        self.__users[row["user_id"]].workspaces.append(self.__workspaces[row["organization_id"]])
            except psycopg.Error as e:
                log.error(f"Error fetching data: {e}")
                return None
            finally:
                self.close()
            log.debug(f"Found {len(self.__workspaces)} workspaces in database")
            log.debug(f"Found {len(self.__users)} users in database")
            self.hydrated = True

    def close(self) -> None:
        if self.conn is not None:
            log.debug("Closing database connection")
            self.conn.close()


def add_args(arg_parser: ArgumentParser) -> None:
    arg_parser.add_argument("--db", dest="db", help="Database name", default="fix-database")
    arg_parser.add_argument("--user", dest="user", help="Database user", default="fixuser")
    arg_parser.add_argument(
        "--password",
        dest="password",
        help="Database password",
        default=os.environ.get("PGPASSWORD", None),
    )
    arg_parser.add_argument("--host", dest="host", help="Database host", default="localhost")
    arg_parser.add_argument("--port", dest="port", help="Database port", default=5432, type=int)
