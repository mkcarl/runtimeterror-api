from firebase_admin import initialize_app, firestore, credentials


cert = credentials.Certificate('service_account.json')
firebaseApp = initialize_app(cert)

firestore = firestore.client(firebaseApp)
