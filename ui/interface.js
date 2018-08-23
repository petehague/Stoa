function getPath(pathname) {
  ws.send(pathname)
}

function commitFile(filename) {
  ws.send("y"+filename)
} 

function newWorktable(filename) {
  cwlname = document.getElementById("cwlfile").value
  ymlname = document.getElementById("ymlfile").value
  if (document.getElementById("keyoff").checked==true) {
    wtxname = document.getElementById("wtxfile").value
    fieldnames = document.getElementById("keyfields").value
    ws.send("C"+cwlname+":"+ymlname+":"+wtxname+":"+fieldnames)
  } else {
    ws.send("C"+cwlname+":"+ymlname)
  }
}

function addRow(tabname) {
  var fields = document.getElementsByClassName("newrow")
  
  for (var i=0;i<fields.length;i++) {
    tabname += ":" + fields[i].value
  }
  ws.send("&"+tabname)
}

ws.onmessage = function(evt) {
  var msg = evt.data
  if (msg.charAt(0)==":") {
    if (document.getElementById("conback") != null) {
      document.getElementById("conback").innerHTML="<p class='console'>"+msg.substr(1)+"</p>"
    } else {
      //This isn't very efficient, but will do for now
      if (document.getElementById("Worktable") != null) {
        ws.send("t"+document.getElementById("monitor").innerHTML)
      }  
    }
    return
  }
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
