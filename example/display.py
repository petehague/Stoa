def stoa(filename):
  print("Running file handler")
  result = "<h2>{}</h2><br />".format(filename)
  for line in open(filename,"r"):
    result += "<p>{}</p>".format(line)
  return result
