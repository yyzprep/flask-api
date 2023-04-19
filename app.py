from flask import Flask, request
import pymysql

app = Flask(__name__)

conn = pymysql.connect(
    host='yyzprep-cluster-do-user-10220084-0.b.db.ondigitalocean.com',
    port=25060,
    user='Ali',
    passwd='DjIH53dF23iCTpy3',
    db='YYZPREP'
)


def runQuery_uplink(query, update=False):
    print(query)
    arr = []
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        if ";" in query:
            queries = query.split(';')
            for q in queries:
                cur.execute(f"{q}")
                arr.append(list(cur.fetchall()))
        else:
            cur.execute(f"{query}")
            if update == True:
                conn.commit()
                return
            return list(cur.fetchall())
        if update == True:
            conn.commit()
            return
        return arr



@app.route('/runQuery', methods=['GET', 'POST'])
def runQuery():
    query = request.args.get('query')
    result = runQuery_uplink(query)
    return {'result': result}


if __name__ == '__main__':
    app.run()
