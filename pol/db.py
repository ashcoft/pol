import psycopg
from psycopg.rows import dict_row


def get_conn(creds, dict_result=False):
    return psycopg.connect(
        host=creds['HOST'],
        port=int(creds['PORT']),
        user=creds['USER'],
        password=creds['PASSWORD'],
        dbname=creds['NAME'],
        autocommit=True,
        row_factory=dict_row if dict_result else None,
    )
