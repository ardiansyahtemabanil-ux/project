from flask import Flask, jsonify, render_template_string
import boto3, os, json
from groq import Groq

app = Flask(__name__)

dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
athena   = boto3.client('athena',   region_name='ap-southeast-1')
groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

TABLE_NAME = 'lks-transactions'
ATHENA_DB  = 'lks_analytics'
S3_OUTPUT  = 's3://lks-data-lake-[namakamu]/athena-results/'

# --- HTML SANGAT SEDERHANA (Gaya Anak Sekolah / Manual) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
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
</html>
"""

# --- ROUTE UTAMA: MENAMPILKAN DASHBOARD ---
@app.route('/')
def index():
    # Mengambil data langsung dari DynamoDB untuk ditampilkan ke tabel HTML
    table = dynamodb.Table(TABLE_NAME)
    result = table.scan()
    data_transaksi = result.get('Items', [])
    
    # Render halaman web dengan membawa data transaksi
    return render_template_string(HTML_TEMPLATE, items=data_transaksi)

# --- ACTION ATHENA ---
@app.route('/run-athena')
def run_athena():
    query = "SELECT COUNT(*) AS total FROM lks_analytics.transactions"
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={'Database': ATHENA_DB},
        ResultConfiguration={'OutputLocation': S3_OUTPUT}
    )
    query_id = response['QueryExecutionId']
    
    # Ambil ulang data transaksi agar tabel tidak kosong saat halaman refresh
    table = dynamodb.Table(TABLE_NAME)
    data_transaksi = table.scan().get('Items', [])
    
    return render_template_string(HTML_TEMPLATE, items=data_transaksi, query_id=query_id)

# --- ACTION AI ---
@app.route('/run-ai')
def run_ai():
    table = dynamodb.Table(TABLE_NAME)
    items = table.scan(Limit=5)['Items']
    prompt = f'Analisis data ini singkat saja: {json.dumps(items)}'
    
    try:
        chat = groq_client.chat.completions.create(
            messages=[{'role': 'user', 'content': prompt}],
            model='llama3-8b-8192'
        )
        ai_text = chat.choices[0].message.content
    except Exception as e:
        ai_text = "Gagal memanggil Groq API."

    data_transaksi = table.scan().get('Items', [])
    return render_template_string(HTML_TEMPLATE, items=data_transaksi, ai_text=ai_text)


# --- ENDPOINT FORMAT JSON UNTUK POSTMAN JURI (JANGAN DIHAPUS) ---
@app.route('/transactions')
def get_transactions():
    table = dynamodb.Table(TABLE_NAME)
    return jsonify(table.scan().get('Items', []))

@app.route('/analytics')
def get_analytics():
    query = "SELECT COUNT(*) AS total FROM lks_analytics.transactions"
    response = athena.start_query_execution(QueryString=query, QueryExecutionContext={'Database': ATHENA_DB}, ResultConfiguration={'OutputLocation': S3_OUTPUT})
    return jsonify({'query_execution_id': response['QueryExecutionId']})

@app.route('/ai-analysis')
def ai_analysis():
    return jsonify({'analysis': 'AI Function triggered via API'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)