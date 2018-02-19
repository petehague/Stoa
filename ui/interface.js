function getPath(pathname) {
  ws.send(pathname)
}

function commitFile(filename) {
  ws.send("y"+filename)
} 

ws.onmessage = function(evt) {
  var msg = evt.data
  if (msg.charAt(0)=="+") {
    document.getElementById("viewer").innerHTML=msg.substr(1)
    document.getElementById("workarea").innerHTML="&nbsp;"
    document.getElementById("workarea").style = "z-index: -1"
    return
  }
  if (msg.charAt(0)=="*") {
    document.getElementById("tablearea").innerHTML=msg.substr(1)
    document.getElementById("workarea").innerHTML="&nbsp;"
    document.getElementById("workarea").style = "z-index: -1"
    return
  }
  if (msg.charAt(0)=="#") {
    document.getElementById("dataarea").innerHTML=msg.substr(1)
    document.getElementById("workarea").innerHTML="&nbsp;"
    document.getElementById("workarea").style = "z-index: -1"
    return
  }
  if (msg.charAt(0)=="t") {
    timedelay = parseInt(msg.substr(1))
    return
  }
  document.getElementById("workarea").innerHTML=msg
  document.getElementById("tablearea").innerHTML=""
  document.getElementById("dataarea").innerHTML=""
  document.getElementById("viewer").innerHTML=""
  document.getElementById("workarea").style = "z-index: 1000"
}

function view(filename) {
  ws.send("D"+filename)
}

function switchto(id) {
  max = document.getElementById("nregs").innerHTML
  for (n=0;n<max;n++) {
    imagetag = document.getElementById("img_"+n)
    if (n==id) {
      imagetag.style="visibility: visible"
    } else {
      imagetag.style="visibility: hidden"
    }
  }
}

function flag(filename, tag) {
  var x = document.getElementById(filename);
  var links = x.getElementsByTagName("a");
  if (tag==1) {
    links[1].style="visibility: hidden";
    links[2].style="visibility: visible";
    ws.send("F"+filename)
  } else {
    links[2].style="visibility: hidden";
    links[1].style="visibility: visible";
    ws.send("U"+filename)
  }
}

function execute(scriptname) {
  ws.send("R"+scriptname)
}
