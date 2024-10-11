import os
import sys
import psycopg
from psycopg.rows import dict_row
from uuid import UUID
from argparse import ArgumentParser
from .logger import log
from .fixresources import FixUser, FixWorkspace, FixCloudAccount, FixRoles, FixUserNotificationSettings
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
        self.__cloud_accounts: dict[UUID, FixCloudAccount] = {}

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
        log.debug(f"Connecting to database {self.db} on {self.host}:{self.port} as {self.user}")
        if self.conn is None:
            try:
                self.conn = psycopg.connect(
                    dbname=self.db, user=self.user, password=self.password, host=self.host, port=self.port
                )
                log.debug("Connection successful")
            except psycopg.DatabaseError as e:
                log.error(f"Error connecting to the database: {e}")
                sys.exit(2)

    def hydrate(self) -> None:
        if self.conn is None:
            self.connect()

        log.debug("Hydrating Fix database data")
        if self.conn is not None:
            try:
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."user" WHERE is_active=true;')
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
                    cursor.execute('SELECT * FROM public."user_role_assignment";')
                    rows = cursor.fetchall()
                    for row in rows:
                        if row["user_id"] not in self.__users or row["workspace_id"] not in self.__workspaces:
                            continue
                        user = self.__users[row["user_id"]]
                        workspace = self.__workspaces[row["workspace_id"]]
                        roles = FixRoles(row["role_names"])
                        user.workspaces.append(workspace)
                        workspace.users.append(user)
                        user.workspace_roles[workspace.id] = roles
                        workspace.user_roles[user.id] = roles
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."organization_owners";')
                    rows = cursor.fetchall()
                    for row in rows:
                        self.__workspaces[row["organization_id"]].owner = self.__users[row["user_id"]]
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."user_notification_settings";')
                    rows = cursor.fetchall()
                    for row in rows:
                        if row["user_id"] in self.__users:
                            user = self.__users[row["user_id"]]
                            user.notification_settings = FixUserNotificationSettings(**row)
                with self.conn.cursor(row_factory=dict_row) as cursor:
                    cursor.execute('SELECT * FROM public."cloud_account";')
                    rows = cursor.fetchall()
                    for row in rows:
                        cloud_account = FixCloudAccount(**row)
                        self.__cloud_accounts[cloud_account.id] = cloud_account
                        if cloud_account.tenant_id in self.__workspaces:
                            self.__workspaces[cloud_account.tenant_id].cloud_accounts.append(cloud_account)
                        else:
                            log.error(f"Data error: cloud account {cloud_account.id} does not have a workspace")
                for workspace in self.__workspaces.values():
                    workspace.update_info()
                for user in self.__users.values():
                    user.update_info()
            except psycopg.Error as e:
                log.error(f"Error fetching data: {e}")
                sys.exit(2)
            finally:
                self.close()
            log.debug(f"Found {len(self.__workspaces)} workspaces in database")
            log.debug(f"Found {len(self.__users)} users in database")
            log.debug(f"Found {len(self.__cloud_accounts)} cloud accounts in database")
            if len(self.__users) == 0 or len(self.__workspaces) == 0:
                log.fatal("No data found in Fix database")
                sys.exit(2)
            self.hydrated = True

    def close(self) -> None:
        if self.conn is not None:
            log.debug("Closing database connection")
            self.conn.close()


def add_args(arg_parser: ArgumentParser) -> None:
    arg_parser.add_argument(
        "--db", dest="db", help="Database name", default=os.environ.get("PGDATABASE", "fix-database")
    )
    arg_parser.add_argument("--user", dest="user", help="Database user", default=os.environ.get("PGUSER", "fixuser"))
    arg_parser.add_argument(
        "--password",
        dest="password",
        help="Database password",
        default=os.environ.get("PGPASSWORD", None),
    )
    arg_parser.add_argument("--host", dest="host", help="Database host", default=os.environ.get("PGHOST", "localhost"))
    arg_parser.add_argument(
        "--port", dest="port", help="Database port", default=os.environ.get("PGPORT", 5432), type=int
    )
