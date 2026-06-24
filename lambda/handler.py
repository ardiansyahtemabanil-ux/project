import json, boto3, uuid, datetime


s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')


BUCKET_NAME   = 'lks-data-lake-[namakamu]'
TABLE_NAME    = 'lks-transactions'
SNS_TOPIC_ARN = 'arn:aws:sns:ap-southeast-1:...:lks-fraud-alert'


def lambda_handler(event, context):
    body = json.loads(event.get('body', '{}'))
    transaction_id = str(uuid.uuid4())
    timestamp = datetime.datetime.utcnow().isoformat()


    # Tambah metadata
    body['transaction_id'] = transaction_id
    body['timestamp'] = timestamp


    # Simpan ke S3
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=f'transactions/{timestamp[:10]}/{transaction_id}.json',
        Body=json.dumps(body),
        ContentType='application/json'
    )


    # Simpan ke DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=body)


    # Deteksi fraud sederhana
    amount = float(body.get('amount', 0))
    if amount > 10000000:  # > 10 juta = fraud
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject='FRAUD ALERT!',
            Message=f'Transaksi mencurigakan: {json.dumps(body)}'
        )
        body['fraud_flag'] = True


    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'OK', 'id': transaction_id})
    }
