from flask import Flask, jsonify, render_template_string
import boto3, os, json
from groq import Groq


app = Flask(__name__)


dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
athena  = boto3.client('athena',   region_name='ap-southeast-1')
groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY'))


TABLE_NAME = 'lks-transactions'
ATHENA_DB  = 'lks_analytics'
S3_OUTPUT  = 's3://lks-data-lake-tema2/'


# Endpoint 1: dashboard
@app.route('/')
def beranda():
    return "Halo, dashboard berhasil diakses!"

# Endpoint 2: Semua transaksi
@app.route('/transactions')
def get_transactions():
    table = dynamodb.Table(TABLE_NAME)
    result = table.scan()
    return jsonify(result['Items'])


# Endpoint 3: Analitik aggregat via Athena
@app.route('/analytics')
def get_analytics():
    query = '''
        SELECT COUNT(*) AS total,
               SUM(amount) AS total_amount,
               COUNT(CASE WHEN fraud_flag=true THEN 1 END) AS fraud_count
        FROM lks_analytics.transactions
    '''
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': ATHENA_DB},
        ResultConfiguration={'OutputLocation': S3_OUTPUT}
    )
    return jsonify({'query_execution_id': response['QueryExecutionId']})


# Endpoint 4: AI Analysis dengan Groq
@app.route('/ai-analysis')
def ai_analysis():
    table = dynamodb.Table(TABLE_NAME)
    items = table.scan(Limit=10)['Items']
    prompt = f'Analisis pola transaksi berikut dan deteksi anomali: {json.dumps(items)}'
    try:
        chat = groq_client.chat.completions.create(
            messages=[{'role': 'user', 'content': prompt}],
            model='llama3-8b-8192'
        )
        return jsonify({'analysis': chat.choices[0].message.content})
    except Exception as e:
        # Fallback mechanism
        return jsonify({'analysis': f'Groq unavailable. Total: {len(items)} transaksi.'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)