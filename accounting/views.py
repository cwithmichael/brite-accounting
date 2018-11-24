# You will probably need more methods from flask but this one is a good start.
from flask import render_template, jsonify, request

# Import things from Flask that we need.
from accounting import app, db

# Import our models
from models import Contact, Invoice, Policy

# Import PolicyAccoutning to get account balance 
from utils import PolicyAccounting
from datetime import date, datetime

import unicodedata

def validReqParams(policy_id, dateReq):
    """Validate the request parameters."""
    if not policy_id or not dateReq: return False
    try:
        datetime.strptime(dateReq, '%Y-%m-%d') # check if date follows format
    except ValueError:
        return False
    try:
        float(policy_id) # make sure policy id is actually a number
    except ValueError:
        return False
    return True

# Routing for the server.
@app.route("/")
def index():
    return render_template('index.html')

@app.route("/invoices")
def show_invoices():
    policy_id  = request.args.get('policy_id', None)
    dateReq  = request.args.get('date_req', None)
    if not validReqParams(policy_id, dateReq):
        return jsonify(error={"message": "invalid params"}), 400
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
    if not validReqParams(policy_id, dateReq):
        return jsonify(error={"message": "invalid params" }), 400
    try:
        pa = PolicyAccounting(int(policy_id))
        return jsonify(balance=pa.return_account_balance(dateReq))
    except:
        return jsonify(notFound={"message" : "policy not found"}), 404