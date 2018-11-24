ko.validation.init({
    registerExtenders: true,
    messagesOnModified: true,
    insertMessages: true,
    parseInputAttributes: true,
    messageTemplate: null
}, true);

var isANumber = function(val) {
    return isNaN(val) == false;
}

var policyViewModel = {
    policyNumber : ko.observable().extend({
        required: {
            message: "The policy number is required"
        },
        validation: {
            validator: isANumber,
            message: "It has to be numeric."
        }
    }),
    date : ko.observable().extend({
        required: {
            message: "A valid date is required"
        } 
    }),
    accountBalance : ko.observable(),
    invoices : ko.observableArray(),
    executeSearch : function() {
        var pn = policyViewModel.policyNumber();
        var date = policyViewModel.date();

        if (policyViewModel.errors().length !== 0) {
            alert(policyViewModel.errors()[0]);
            return;
        }
       
        $.ajax({
            type: "GET",
            url: encodeURI("http://localhost:5000/account_balance?policy_id=" + pn +"&date_req=" + date), 
            error: function(xhr, status) {
                policyViewModel.accountBalance("");
                alert ("Error: Policy not found" ); 
            },
            success: function(data) {
                if (data.balance) {
                    policyViewModel.accountBalance("Account Balance: " + data.balance);
                }
            }
        });

        $.ajax({
            type: "GET",
            url: encodeURI("http://localhost:5000/invoices?policy_id=" + pn +"&date_req=" + date), 
            success: function(data) {
                if (data.invoices) {
                    policyViewModel.invoices(data.invoices);
                }
            }
        });
    }
}

policyViewModel.errors = ko.validation.group(policyViewModel);

ko.applyBindings(policyViewModel);