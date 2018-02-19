var cc = new samp.ClientTracker();
var callHandler = cc.callHandler;
var tabBuffer = ""
var meta = {
    "samp.name": "Stoa",
    "samp.description": "Web front end for Stoa script manager",
    //"samp.icon.url": baseUrl + "clientIcon.gif"
};
var subs = cc.calculateSubscriptions();
var connector = new samp.Connector("STOA", meta, cc, subs);

//connector.register()
//connector.update()

function doSend(connection) {
  var msg = new samp.Message("table.load.votable", {"url": tabBuffer});
  connection.notifyAll([msg]);
}

function sendTable(tabURL) {
  tabBuffer = tabURL
  connector.runWithConnection(doSend)
}

callHandler["samp.app.ping"] = function(senderId, message, isCall) {
  alert("ping")
}

callHandler["table.load.votable"] = function(senderId, message, isCall) {
  alert("table")
}
