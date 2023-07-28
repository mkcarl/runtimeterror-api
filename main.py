from flask import Flask, request, jsonify
from flask_cors import CORS
import functools

from firebase import firestore

app = Flask(__name__)
CORS(app)

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
    requests = firestore.collection('Requests')
    '''
        Attachment: map | null, 
        Body: string, 
        Conversation: array,
        Sender_email: string, 
        Status: string, 
        Title: string, 
        Timestamp: integer
    '''
    requests_list = []
    for doc in requests.get():
        request = doc.to_dict()
        request['id'] = doc.id
        requests_list.append(request)

    return requests_list

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
        orders_list = []
        for doc in orders.get():
            order  = doc.to_dict()
            order['id'] = doc.id
            orders_list.append(order)

        return orders_list


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
        'Subject': 'Order Request 1',
        'Status': 'approved',
        'Timestamp': 0,
    })

    firestore.collection('Requests').document(req2_id).set({
        'Attachments': {
            'eggplant': 220,
            'potato': 20
        },
        'Body': 'bro, get me these',
        'Conversation': [],
        'Sender_email': 'mkcarl.dev@gmail.com',
        'Subject': 'Order Request 2',
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

@app.route('/dashboard', methods=['GET'])
def dashboard():
    if request.method == 'GET':
        orders = firestore.collection('Orders')
        requests  = firestore.collection('Requests')
        inventory = firestore.collection('InventoryStock')

        fulfilledOrders = orders.where('fulfilled', '==', True).get()
        fulfilledOrdersItems = functools.reduce(lambda acc, curr: acc+list(curr.get('items').items()), fulfilledOrders, [])

        allInventory = list(x.to_dict() for x in inventory.get())
        revenue  = 0
        items_out = 0
        for (item, qty) in fulfilledOrdersItems:
            target = filter(lambda x : x['Name'] == item, allInventory).__next__()
            revenue = revenue + target['PricePerUnit'] * qty
            items_out = items_out + qty

        def mergeItemsIntoDict(acc, curr):
            if curr[0] in acc:
                acc[curr[0]] += curr[1]
            else:
                acc[curr[0]] = curr[1]
            return acc

        reducedFulfilledOrderItems = functools.reduce(mergeItemsIntoDict, fulfilledOrdersItems, {})
        # for dashboard data ^

        data = {
            'orders': {
                'fulfilled': orders.where('fulfilled', '==', True).count().get().pop().pop().value,
                'pending': orders.where('fulfilled', '==', False).count().get().pop().pop().value,
            },
            'requests': {
                'approved': requests.where('Status', '==', 'approved').count().get().pop().pop().value,
                'pending': requests.where('Status', '==', 'pending').count().get().pop().pop().value,
                'rejected': requests.where('Status', '==', 'rejected').count().get().pop().pop().value,
            },
            'inventory': {
                'in': None,
                'out': items_out
            },
            'revenue': revenue,
            'inventoryItemOut': reducedFulfilledOrderItems
        }
        print(data)
        return data


"""
    program flow 
        1. customer send email
        2. email parser extract information, save to firestore (Requests)
        3. data analyst check incoming requests, if got problem, communicate with customer, if ok, add to Orders
        4. inventory controller manages all the orders, approve based on inventory stock
        
"""
if __name__ == "__main__":
    from waitress import serve
    print(f'Running on http://localhost:8080')
    serve(app, host="0.0.0.0", port=8080)
