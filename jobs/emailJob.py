# when email comes in,
# parse email using email parser
# save to firestore
import base64
import email
import json
import os
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from firebase import firestore

load_dotenv()

# authenticate with gmail api
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            os.getenv('GMAIL_CREDENTIAL_JSON_PATH'), SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.json', 'w') as token:
        token.write(creds.to_json())

# Build the Gmail API service
service = build('gmail', 'v1', credentials=creds)


def extract_email():
    unread_emails = get_unread_emails()


def is_csv(filename):
    return filename.lower().endswith('.xlsx')


def get_unread_emails():
    results = service.users().messages().list(userId='me', q='is:unread').execute()
    return results.get('messages', [])


def reply_email(message, reply_content, attachment_path=None):
    reply_message = MIMEMultipart()

    reply_text = MIMEText(reply_content + f'\n\n This is an automated reply.')

    reply_message['To'] = message['From']
    reply_message['Subject'] = 'Re: ' + message['Subject']
    reply_message['In-Reply-To'] = message['Message-ID']
    reply_message['References'] = message['Message-ID']

    reply_message.attach(reply_text)

    try:

        if attachment_path:
            with open(attachment_path, 'rb') as f:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition',
                                      f'attachment; filename="{os.path.basename(attachment_path)}"')
                reply_message.attach(attachment)
    except Exception as e:
        print('Error: Unable to attach file')
        print(e)

    raw = base64.urlsafe_b64encode(reply_message.as_string().encode('utf-8')).decode('utf-8')
    body = {'raw': raw}

    service.users().messages().send(userId='me', body=body).execute()
    print(f'Replied to {message["From"]} about {message["Subject"]}')


def extract_info(message):
    info = {}
    email_id = message['id']
    mark_email_as_read(email_id)
    gmail = service.users().messages().get(userId='me', id=email_id, format='raw').execute()
    msg_bytes = base64.urlsafe_b64decode(gmail['raw'])
    msg = email.message_from_bytes(msg_bytes)

    # Extract the title, and sender email
    info['subject'] = msg['subject']
    info['sender'] = msg['from']

    # Extract the email body
    for part in msg.walk():
        if part.get_content_type() == 'text/plain':
            info['body'] = part.get_payload(decode=True).decode('utf-8')
            break

    # Extract attachments if any
    for part in msg.walk():
        if part.get_filename():
            attachment_data = part.get_payload(decode=True)
            if attachment_data:
                path = part.get_filename()

                if not path.endswith('.xlsx'):
                    reply_email(msg, f'Please ensure that your attachment is an excel file.')
                    continue

                with open(path, 'wb') as f:
                    f.write(attachment_data)

                df = pd.read_excel(path)

                expected_columns = ['items', 'quantity']
                if not set(expected_columns).issubset(df.columns):
                    # reply_email(msg, f'Please ensure that your excel file has the following columns: {expected_columns}')
                    continue

                info['attachment'] = df.set_index('items')['quantity'].to_dict()
    if not info.get('attachment'):
        reply_email(msg,
                    f'Please ensure that your email has an excel attachment following the format. Attached is the template file. Do download and edit the attached file.',
                    r'template.xlsx')
    else:
        reply_email(msg, f'Thank you for your request. We will get back to you shortly.')

    return info


def mark_email_as_read(email_id):
    try:
        # Modify the email by removing the 'UNREAD' label
        service.users().messages().modify(userId='me', id=email_id, body={'removeLabelIds': ['UNREAD']}).execute()
        print(f"Email with ID {email_id} marked as read.")
    except Exception as e:
        print("Error marking email as read:", e)


while True:
    print(f'Checking for new emails...')
    mails = get_unread_emails()
    print(f'Found {len(mails)} new emails.')

    for message in mails:
        info = extract_info(message)

        if not info.get('attachment'):
            continue

        firestore.collection('Requests').add(
            {
                'Subject': info.get('subject'),
                'Sender': info.get('sender'),
                'Body': info.get('body'),
                'Attachment': info.get('attachment') or {},
                'Status': 'pending',
                'Conversation': [],
                'timestamp': time.time_ns() // 1000000
            }
        )

    time.sleep(10)
