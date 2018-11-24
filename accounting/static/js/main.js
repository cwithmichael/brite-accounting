var policyViewModel = {
    policyNumber : ko.observable(),
    date : ko.observable(),
    accountBalance : ko.observable(),
    invoices : ko.observableArray(),
    executeSearch : function() {
        var pn = policyViewModel.policyNumber();
        var date = policyViewModel.date();
       
        $.get(encodeURI("http://localhost:5000/account_balance?policy_id=" + pn +"&date_req=" + date), 
            function(data) {
                policyViewModel.accountBalance("Account Balance:" + data.balance);
            }
        );

        $.get(encodeURI("http://localhost:5000/invoices?policy_id=" + pn +"&date_req=" + date), 
            function(data) {
                policyViewModel.invoices(data.invoices);
            }
        );
    }
}

ko.applyBindings(policyViewModel);