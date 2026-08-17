"""Generic class"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.utils.config_loader import get_config
from src.utils.log_helper import logger
from src.utils.singleton_meta import SingletonMeta

load_dotenv()


class Database(metaclass=SingletonMeta):
    """Generic class to connect to the database using SQLAlchemy."""

    def __init__(self, db_schema: str, db_name="PostgreSQL"):
        logger.info("Creating %s DB conn..", db_schema)
        self.__db_name = db_name
        self.__db_schema = db_schema
        self.engine = self.__create_engine()
        self.session = sessionmaker(bind=self.engine)

    def __create_engine(self):
        """Create an engine to connect to the database.
        :return: engine
        """
        conn_str = self.__get_conn_str()
        try:
            # print("conn_str: %s ", conn_str)
            logger.info('Connecting to "%s" database..', self.__db_name)
            engine = create_engine(conn_str, echo=True)
            return engine
        except Exception as err:
            logger.info("conn_str: %s ", conn_str)
            logger.error(err)
            raise

    def __get_conn_str(self):
        conn_details = get_config("database")
        user, password, host, port = (
            conn_details["user"],
            os.getenv("POSTGRES_PASSWORD"),
            conn_details["host"],
            conn_details["port"],
        )
        password = password.replace("@", "%40")

        # Format the DATABASE_URL using the dictionary values
        conn_str = (
            f"{self.__db_name.lower()}+psycopg2://"
            f"{user}:{password}@{host}:{port}/{self.__db_schema}?sslmode=require"
        )

        # postgresql://doadmin:show-password@schengenvisa-do-user-29480745-0.h.db.ondigitalocean.com:25060/schengendb?sslmode=require

        return conn_str


if __name__ == "__main__":
    print(Database(db_schema="User_Management"))
