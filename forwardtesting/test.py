import psycopg2
import os

username = os.environ['POSTGRE_USER']
password = os.environ['POSTGRE_PASSWORD']
host = os.environ['POSTGRE_HOST']

conn = psycopg2.connect(host=host, database='forwardtesting',
                        user=username, password=password)
cursor = conn.cursor()

cmds = (
    """
    CREATE TABLE positions (
        position_id VARCHAR(255) PRIMARY KEY,
        position_type VARCHAR(255),
        num_positions INTEGER,
        avg_cost float(2)
    )""",

    """
    CREATE TABLE portfolio (
        position_id VARCHAR(255),
        portfolio_value float(2) NOT NULL, 
        time_last_updated TIMESTAMP NOT NULL,
        FOREIGN KEY (position_id) REFERENCES positions (position_id)
    )""",

    """
    INSERT INTO portfolio(portfolio_value, time_last_updated) 
    VALUES (96.81, 'Jan 1, 2020')
    """,

    """
    INSERT INTO portfolio(portfolio_value, time_last_updated) 
    VALUES (100.01, 'Feb 1, 2020')
    """,

    """
    SELECT * FROM portfolio
    """,
)

for cmd in cmds:
    cursor.execute(cmd)

print(cursor.fetchall())

conn.close()

# conn.commit()
