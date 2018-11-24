#!/user/bin/env python2.7

from datetime import date, datetime
from dateutil.relativedelta import relativedelta

from accounting import db
from models import Contact, Invoice, Payment, Policy

"""
#######################################################
This is the base code for the engineer project.
#######################################################
"""

class PolicyAccounting(object):
    """Each policy has its own instance of accounting."""
    def __init__(self, policy_id):
        self.policy = Policy.query.filter_by(id=policy_id).one()

        if not self.policy.invoices:
            self.make_invoices()

    def return_account_balance(self, date_cursor=None):
        """Return the policy's account balance."""

        if not date_cursor:
            date_cursor = datetime.now().date()

        # Filters the policy's invoices for all invoices that have
        # a billing date before or on the date provided by the date_cursor 
        # parameter.
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.bill_date <= date_cursor)\
                                .filter(Invoice.deleted == False)\
                                .order_by(Invoice.bill_date)\
                                .all()
        due_now = 0
        for invoice in invoices:
            due_now += invoice.amount_due

        # Filters the policy's payments for all payments that have
        # a transaction date before or on the date provided by the date_cursor 
        # parameter.
        payments = Payment.query.filter_by(policy_id=self.policy.id)\
                                .filter(Payment.transaction_date <= date_cursor)\
                                .all()
        for payment in payments:
            due_now -= payment.amount_paid

        return due_now

    def make_payment(self, contact_id=None, date_cursor=None, amount=0):
        """Add a payment to the policy.
        
        Creates a new payment for the policy and persists it 
        to the data store for the insured (specified by contact_id) 
        """

        if not date_cursor:
            date_cursor = datetime.now().date()

        if not contact_id:
            try:
                contact_id = self.policy.named_insured
            except:
                pass

        payment = Payment(self.policy.id,
                          contact_id,
                          amount,
                          date_cursor)
        db.session.add(payment)
        db.session.commit()

        return payment

    def evaluate_cancellation_pending_due_to_non_pay(self, date_cursor=None):
        """Determine if the current policy is in danger of cancellation
         
         If this function returns true, an invoice
         on a policy has passed the due date without
         being paid in full. However, it has not necessarily
         made it to the cancel_date yet.
        """
        if not date_cursor:
            date_cursor = datetime.now().date()
        # Filters invoices for all invoices with a passed due date from
        # the date_cursor parameter 
        invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                .filter(Invoice.due_date <= date_cursor)\
                                .filter(Invoice.due_date < Invoice.cancel_date)\
                                .filter(Invoice.deleted == False)\
                                .order_by(Invoice.bill_date)\
                                .all()
        for invoice in invoices:
            if not self.return_account_balance(invoice.due_date):
                continue
            else:
                return True
        else:
            return False

    def evaluate_cancel(self, date_cursor=None, manual_cancellation=False, cancellation_reason=None):
        """Determine if the current policy should be canceled."""
        if not date_cursor:
            date_cursor = datetime.now().date()
        
        if manual_cancellation:
            print "THIS POLICY IS GETTING CANCELED"
            db.session.query(Policy).filter_by(id=self.policy.id).update({"status": "Canceled"})
            db.session.query(Policy).filter_by(id=self.policy.id)\
                .update({"cancellation_date": date_cursor})
            db.session.query(Policy).filter_by(id=self.policy.id)\
                .update({"cancellation_reason": cancellation_reason})
        else:
            # Filters invoices for all invoices with a cancel date that has not passed
            # the date provided to the date_cursor parameter
            invoices = Invoice.query.filter_by(policy_id=self.policy.id)\
                                    .filter(Invoice.cancel_date <= date_cursor)\
                                    .filter(Invoice.deleted == False)\
                                    .order_by(Invoice.bill_date)\
                                    .all()

            for invoice in invoices:
                # If there is no balance due, then just continue
                if not self.return_account_balance(invoice.cancel_date):
                    continue
                else:
                    print "THIS POLICY SHOULD HAVE CANCELED"
                    db.session.query(Policy).filter_by(id=self.policy.id).update({"status": "Canceled"})
                    db.session.query(Policy).filter_by(id=self.policy.id)\
                        .update({"cancellation_date": invoice.cancel_date})
                    db.session.query(Policy).filter_by(id=self.policy.id)\
                        .update({"cancellation_reason": "Cancellation Date Reached"})
                    break
            else:
                print "THIS POLICY SHOULD NOT CANCEL"
        
        db.session.commit()

    def change_schedule(self, new_schedule):
        """Change the billing schedule after policy creation."""
        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12}
        if new_schedule not in billing_schedules: return
        if self.policy.billing_schedule == new_schedule: return
        
        # Find all the invoices for the policy and mark them as deleted
        db.session.query(Invoice).filter_by(policy_id=self.policy.id).update({"deleted": True})
        # Change the billing schedule
        db.session.query(Policy).filter_by(id=self.policy.id).update({"billing_schedule": new_schedule})
        self.make_invoices()

    def make_invoices(self):
        """Create invoices for the policy.

        TODO: Improve the DRYness of this method
        """
        for invoice in self.policy.invoices:
            if not invoice.deleted:
                db.session.delete(invoice) # clear out any preexisting invoices 

        billing_schedules = {'Annual': None, 'Two-Pay': 2, 'Semi-Annual': 3, 'Quarterly': 4, 'Monthly': 12}
        billing_months = billing_schedules.get(self.policy.billing_schedule)
        invoices = []
        total = 0

        # The initial amount_due for the first invoice 
        # will be the amount due for the year
        first_invoice = Invoice(self.policy.id,
                                self.policy.effective_date, # bill_date
                                self.policy.effective_date + relativedelta(months=1), # due_date
                                self.policy.effective_date + relativedelta(months=1, days=14), # cancel_date
                                self.policy.annual_premium)
        invoices.append(first_invoice)

        # The insured has chosen to pay once a year
        if self.policy.billing_schedule == "Annual":
            pass #nothing to do since we only have one invoice that was created above 
        # The insured has chosen to pay twice a year
        elif self.policy.billing_schedule == "Two-Pay":
            amount_due = self.policy.annual_premium / billing_months # The amount due split evenly
            first_invoice.amount_due = first_invoice.amount_due / billing_months
            total += first_invoice.amount_due
            for i in range(1, billing_months):
                # The next invoice comes 6 months after the policy goes into effect
                months_after_eff_date = i*6
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                total += amount_due
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_months)
                # Handle the case of there being an amount left over after splitting the payments
                # There are other ways to handle this, but this is the approach taken for time's sake
                if i == billing_months-1 and total != self.policy.annual_premium:
                    invoice.amount_due += (self.policy.annual_premium - total)
                invoices.append(invoice)
        # The insured has chosen to pay every 4 months
        elif self.policy.billing_schedule == "Quarterly":
            amount_due = self.policy.annual_premium / billing_months # The amount due split evenly
            first_invoice.amount_due = first_invoice.amount_due / billing_months
            total += first_invoice.amount_due
            for i in range(1, billing_months):
                # The invoices come every 3 months after the policy goes into effect
                months_after_eff_date = i*3
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                total += amount_due
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  self.policy.annual_premium / billing_months)
                # Handle the case of there being an amount left over after splitting the payments
                # There are other ways to handle this, but this is the approach taken for time's sake
                if i == billing_months-1 and total != self.policy.annual_premium:
                    invoice.amount_due += (self.policy.annual_premium - total)
                invoices.append(invoice)
        # The insured has chosen to pay once a month
        elif self.policy.billing_schedule == "Monthly":
            amount_due = self.policy.annual_premium / billing_months # The amount due split evenly
            first_invoice.amount_due = first_invoice.amount_due / billing_months
            total += first_invoice.amount_due
            for i in range(1, billing_months):
                # The invoices come every month after the policy goes into effect
                months_after_eff_date = i
                bill_date = self.policy.effective_date + relativedelta(months=months_after_eff_date)
                total += amount_due
                invoice = Invoice(self.policy.id,
                                  bill_date,
                                  bill_date + relativedelta(months=1),
                                  bill_date + relativedelta(months=1, days=14),
                                  amount_due)
                # Handle the case of there being an amount left over after splitting the payments
                # There are other ways to handle this, but this is the approach taken for time's sake
                if i == billing_months-1 and total != self.policy.annual_premium:
                    invoice.amount_due += (self.policy.annual_premium - total)
                invoices.append(invoice)
        # Received an unknown billing schedule
        else:
            print "You have chosen a bad billing schedule."

        for invoice in invoices:
            db.session.add(invoice)
        db.session.commit()

################################
# The functions below are for the db and 
# shouldn't need to be edited.
################################
def build_or_refresh_db():
    db.drop_all()
    db.create_all()
    insert_data()
    print "DB Ready!"

def insert_data():
    #Contacts
    contacts = []
    john_doe_agent = Contact('John Doe', 'Agent')
    contacts.append(john_doe_agent)
    john_doe_insured = Contact('John Doe', 'Named Insured')
    contacts.append(john_doe_insured)
    bob_smith = Contact('Bob Smith', 'Agent')
    contacts.append(bob_smith)
    anna_white = Contact('Anna White', 'Named Insured')
    contacts.append(anna_white)
    joe_lee = Contact('Joe Lee', 'Agent')
    contacts.append(joe_lee)
    ryan_bucket = Contact('Ryan Bucket', 'Named Insured')
    contacts.append(ryan_bucket)

    for contact in contacts:
        db.session.add(contact)
    db.session.commit()

    policies = []
    p1 = Policy('Policy One', date(2015, 1, 1), 365)
    p1.billing_schedule = 'Annual'
    p1.agent = bob_smith.id
    policies.append(p1)

    p2 = Policy('Policy Two', date(2015, 2, 1), 1600)
    p2.billing_schedule = 'Quarterly'
    p2.named_insured = anna_white.id
    p2.agent = joe_lee.id
    policies.append(p2)

    p3 = Policy('Policy Three', date(2015, 1, 1), 1200)
    p3.billing_schedule = 'Monthly'
    p3.named_insured = ryan_bucket.id
    p3.agent = john_doe_agent.id
    policies.append(p3)

    for policy in policies:
        db.session.add(policy)
    db.session.commit()

    for policy in policies:
        PolicyAccounting(policy.id)

    payment_for_p2 = Payment(p2.id, anna_white.id, 400, date(2015, 2, 1))
    db.session.add(payment_for_p2)
    db.session.commit()

