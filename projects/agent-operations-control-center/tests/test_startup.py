from concurrent.futures import ThreadPoolExecutor
import os
import secrets
from threading import Barrier
import uuid

import psycopg
from psycopg import sql

from ops_center.config import Settings
from ops_center.store import Store


def test_concurrent_schema_initialization_is_serialized():
    url=os.environ['DATABASE_URL']
    schema='ops_boot_test_'+uuid.uuid4().hex
    principals=[{'name':'viewer','role':'viewer','project':'lab','token':secrets.token_urlsafe(32)}]
    with psycopg.connect(url,autocommit=True) as db:
        db.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        barrier=Barrier(8)
        def initialize(index):
            barrier.wait()
            Store(Settings(url,principals,schema)).initialize()
        with ThreadPoolExecutor(max_workers=8) as executor:
            for result in executor.map(initialize,range(8)):
                assert result is None
    finally:
        assert schema.startswith('ops_boot_test_') and len(schema)==46
        with psycopg.connect(url,autocommit=True) as db:
            db.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
