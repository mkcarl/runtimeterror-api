from flask import Flask, request, jsonify

from firebase import firestore

app = Flask(__name__)


@app.route('/')
def index():
    return 'Hello World!'


@app.route('/hello')
def hello():
    test = firestore.collection('test').get()
    return str(','.join([doc.id for doc in test]))


@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    inventory = firestore.collection('InventoryStock').get()
    inventory_json = jsonify([doc.to_dict() for doc in inventory])

    if request.method == 'GET':
        return inventory_json
    elif request.method == 'POST':
        return 'POST'


@app.route('/requests', methods=['GET'])
def requests():
    requests = firestore.collection('Requests').get()
    '''
        Attachment: map | null, 
        Body: string, 
        Conversation: array,
        Sender_email: string, 
        Status: string, 
        Title: string, 
        Timestamp: integer
    '''
    requests_json = jsonify([doc.to_dict() for doc in requests])
    return requests_json


@app.route('/requests/approve', methods=['POST'])
def reqApprove():
    if request.method == 'POST':
        body = request.json

        doc = firestore.collection('Requests').document(body['id'])
        doc.update({
            'Status': 'approved'
        })

        orders = firestore.collection('Orders')
        new_order = orders.add({
            'items': doc.get().to_dict()['Attachments'],
            'fulfilled': False,
            'request': body['id'],
        })

        return 'Approved request ' + body['id'] + ' and added to orders at' + new_order[1].id


@app.route('/orders', methods=['GET'])
def orders():
    orders = firestore.collection('Orders')
    if request.method == 'GET':
        orders_json = jsonify([doc.to_dict() for doc in orders.get()])
        return orders_json


@app.route('/orders/approve', methods=['POST'])
def approve():
    if request.method == 'POST':
        body = request.json

        doc = firestore.collection('Orders').document(body['id'])
        doc.update({
            'fulfilled': True
        })
        return 'Approved order ' + body['id']


@app.route('/reset', methods=['GET'])
def reset():
    for doc in firestore.collection('Orders').get():
        doc.reference.delete()
    for doc in firestore.collection('Requests').get():
        doc.reference.delete()

    req1_id = 'req1'
    req2_id = 'req2'
    order1_id = 'order1'

    firestore.collection('Requests').document(req1_id).set({
        'Attachments': {
            'carrot': 10,
            'potato': 20
        },
        'Body': 'Hi, i want to order these',
        'Conversation': [],
        'Sender_email': 'mkcarl.dev@gmail.com',
        'Status': 'approved',
        'Timestamp': 0,
    })

    firestore.collection('Requests').document(req2_id).set({
        'Attachments': {
            'chicken': 220,
            'potato': 20
        },
        'Body': 'bro, get me these',
        'Conversation': [],
        'Sender_email': 'mkcarl.dev@gmail.com',
        'Status': 'pending',
        'Timestamp': 0,
    })

    firestore.collection('Orders').document(order1_id).set({
        'items': {'carrot': 10,
                  'potato': 20,
                  },
        'fulfilled': False,
        'request': req1_id,
    })

    return 'reset done'

"""
    program flow 
        1. customer send email
        2. email parser extract information, save to firestore (Requests)
        3. data analyst check incoming requests, if got problem, communicate with customer, if ok, add to Orders
        4. inventory controller manages all the orders, approve based on inventory stock
        
"""
