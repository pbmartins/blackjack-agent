import sqlite3
from casino import main as casino_main

def main():
    conn = sqlite3.connect('tables.sqlite')
    table_name = 'StateAction'
    table_query = 'CREATE TABLE IF NOT EXISTS [' + table_name + '] (' + \
        '[StateID]          INTEGER PRIMARY KEY AUTOINCREMENT,' + \
        '[PlayerPoints]     INTEGER NOT NULL,' + \
        '[DealerPoints]     INTEGER NOT NULL,' + \
        '[SoftHand]         INTEGER NOT NULL,' + \
        '[FirstTurn]        INTEGER NOT NULL,' + \
        '[Action]           TEXT NOT NULL,' + \
        '[Probability]      REAL NOT NULL);'
    conn.execute(table_query)
    p = lambda ft: 0.25 if ft == 1 else 1/3
    plays = lambda ft: ['s', 'h', 'u', 'd'] if ft == 1 else ['s', 'h', 'u']
    states = [(pp, dp, sh, ft, a, p(ft)) for pp in range(3, 21) \
            for dp in range(2, 22) for sh in [0, 1] for ft in [0, 1] \
            for a in plays(ft)]
    states_query = 'INSERT OR IGNORE INTO ' + table_name + \
        ' (PlayerPoints, DealerPoints, SoftHand, FirstTurn, Action, Probability)' + \
        ' VALUES (?, ?, ?, ?, ?, ?)'
    conn.executemany(states_query, states)
    conn.commit()

    n_games = 50000000
    print("Training agent with " + str(n_games)+ ":")
    casino_main(table_name=table_name, n_games=n_games, train=True)


if __name__ == '__main__':
    main()
