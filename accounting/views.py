# You will probably need more methods from flask but this one is a good start.
from flask import render_template, jsonify, request

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy

# Import PolicyAccoutning to get account balance 
from utils import PolicyAccounting
from datetime import date

# Routing for the server.
@app.route("/")
def index():
    # You will need to serve something up here.
    return render_template('index.html')

@app.route("/invoices")
def show_invoices():
    policy_id  = request.args.get('policy_id', None)
    dateReq  = request.args.get('date_req', None)
    # return all the invoices for the policy
    invoices = Invoice.query.filter_by(policy_id=policy_id)\
                                    .filter(Invoice.bill_date <= dateReq)\
                                    .order_by(Invoice.bill_date)\
                                    .all()
    return jsonify(invoices=[i.serialize() for i in invoices])
    
@app.route("/account_balance")
def show_account_balance():
    policy_id  = request.args.get('policy_id', None)
    dateReq  = request.args.get('date_req', None)
    pa = PolicyAccounting(int(policy_id))
    return jsonify(balance=pa.return_account_balance(dateReq))