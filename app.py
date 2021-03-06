import os

import flask
import operator

import math

from flask import request
from sqlalchemy import TEXT
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker, mapper
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import BIGINT, DOUBLE_PRECISION
from werkzeug.exceptions import BadRequest
from sqlalchemy import Table, Column

app = flask.Flask(__name__)
db_user = os.environ['DB_USER']
db_pass = os.environ['DB_PASS']
db_host = os.environ['DB_HOST']

db_url = 'postgresql://{0}:{1}@{2}'.format(db_user, db_pass, db_host)
engine = create_engine(db_url)
metadata = MetaData()
db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
metadata.create_all(bind=engine)


# http://flask.pocoo.org/docs/0.12/patterns/sqlalchemy/#manual-object-relational-mapping
@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


class WordVector(object):
    query = db_session.query_property()

    def __init__(self, string, vector):
        self.string = string
        self.vector = vector

    def __repr__(self):
        return '<Word %r>' % (self.string)


wordVectors = Table('glove_vectors', metadata,
                    Column('id', BIGINT, primary_key=True, nullable=False),
                    Column('string', TEXT, unique=True, nullable=False),
                    Column('vector', postgresql.ARRAY(DOUBLE_PRECISION, dimensions=1)),
                    )
mapper(WordVector, wordVectors)


# fastest cosine similarity
# http://stackoverflow.com/a/33754650
def dot_product(v1, v2):
    return sum(map(operator.mul, v1, v2))


def vector_cos(v1, v2):
    prod = dot_product(v1, v2)
    len1 = math.sqrt(dot_product(v1, v1))
    len2 = math.sqrt(dot_product(v2, v2))
    return prod / (len1 * len2)


@app.route('/')
def health():
    return 'ok'


@app.route('/compare')
def compare():
    '''
    curl 'localhost:5000/compare?string1=france&string2=paris'
    :return:
    {
        "result": 0.7916327755099385
    }
    '''
    string1 = request.args.get('string1')
    string2 = request.args.get('string2')
    if string1 is None or string2 is None:
        return BadRequest('string1 or string2 query param missing')

    vector1 = WordVector.query.filter(WordVector.string == string1).first()
    vector2 = WordVector.query.filter(WordVector.string == string2).first()
    result = {'result': None}
    if vector1 is None or vector2 is None:
        return flask.jsonify(result)

    result['result'] = vector_cos(vector1.vector, vector2.vector)
    return flask.jsonify(result)


# https://stackoverflow.com/questions/8603088/sqlalchemy-in-clause
@app.route('/vectors', methods=['POST'])
def retrieve_vectors():
    '''
    curl --header "Content-type: application/json" -XPOST -d '{"strings": ["hello", "united states"]}' http://localhost:5000/vectors
    :return:
    [
        {
            "string": "hello",
            "vector": [
                0.25233,
                0.10176,
                -0.67485,
                ...
            ]
        },
        {
            "string": "united states",
            "vector": null
        }
    ]
    '''
    request_json = request.get_json()
    print request_json
    if request_json is None or 'strings' not in request_json:
        return BadRequest(
            'json not formatted properly, expecting json of type "strings": ["string1", "string2", string3"]')

    request_strings = set(request_json['strings'])
    sql_query_results = WordVector.query.filter(WordVector.string.in_(request_strings))

    result = []

    for sql_query_result in sql_query_results:
        result.append({
            "string": sql_query_result.string,
            "vector": sql_query_result.vector
        })
        request_strings.remove(sql_query_result.string)

    for remaining_str in request_strings:
        result.append({
            "string": remaining_str,
            "vector": None
        })

    return flask.jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

