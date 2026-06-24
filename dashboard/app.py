from flask import Flask, jsonify, render_template_string
import boto3, os, json
from groq import Groq


app = Flask(__name__)


dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
athena  = boto3.client('athena',   region_name='ap-southeast-1')
groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY'))


TABLE_NAME = 'lks-transactions'
ATHENA_DB  = 'lks_analytics'
S3_OUTPUT  = 's3://lks-data-lake-tema2/athena-results/'


# Endpoint 1: dashboard
@app.route('/')
def beranda():
    return "<!DOCTYPE html>
<html>
<head>
    <title>Dashboard LKS 2026</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; bg-color: #f0f0f0; }
        h1 { color: #333; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; background: white; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #e0e0e0; }
        .box { border: 1px solid #999; padding: 15px; margin-top: 15px; background: #fff; }
        button { padding: 8px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #45a049; }
    </style>
</head>
<body>

    <h1>Monitoring Transaksi - LKS CC 2026</h1>
    <p>Provinsi Lampung</p>

    <div class="box">
        <h3>Daftar Transaksi (DynamoDB)</h3>
        <table>
            <thead>
                <tr>
                    <th>Transaction ID</th>
                    <th>User ID</th>
                    <th>Amount</th>
                </tr>
            </thead>
            <tbody>
                {% for item in items %}
                <tr>
                    <td>{{ item.transaction_id }}</td>
                    <td>{{ item.user_id }}</td>
                    <td>Rp {{ item.amount }}</td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="3">Tidak ada data transaksi.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="box">
        <h3>Menu Analitik (Amazon Athena)</h3>
        <p>Klik tombol di bawah untuk menjalankan Query SQL di S3 via Athena:</p>
        <form action="/run-athena" method="GET">
            <button type="submit">Jalankan Query Athena</button>
        </form>
        {% if query_id %}
        <p style="color: blue; font-family: monospace;">Query Berhasil Dikirim! ID: {{ query_id }}</p>
        {% endif %}
    </div>

    <div class="box">
        <h3>Analisis AI (Groq API)</h3>
        <form action="/run-ai" method="GET">
            <button type="submit" style="background-color: #008CBA;">Minta Analisis Llama3</button>
        </form>
        {% if ai_text %}
        <p><b>Hasil Analisis:</b></p>
        <div style="background: #eef; padding: 10px; border-left: 4px solid #008CBA;">
            {{ ai_text }}
        </div>
        {% endif %}
    </div>

</body>
</html>"

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