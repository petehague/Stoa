from multiprocessing import Queue


class userState():
    def __init__(self):
        """
        Class to keep track of the state of each user

        """
        self.folder = ""
        self.ip = ""
        self.run = "Nothing"
        self.proc = None
        self.buff = []
        self.q = Queue()
        self.procreport = ""
        self.siteroot = ""
        self.wsroot = ""

    def clearBuffer(self):
        """
        Clear the buffer

        :return:
        """
        self.buff = []

    def appendBuffer(self, newEntry):
        """
        Add a string to the buffer

        :param newEntry: The string to add
        :return: None
        """
        self.buff.append(newEntry)

    def appendQueue(self):
        """
        Add the contents of the process queue to the buffer

        :return: None
        """
        if not self.q.empty():
            self.buff.append(self.q.get())

    def finalise(self):
        """
        Checks if the process has finished, and if so performs finalisation operations

        :return: None
        """
        if self.q.empty():
            if self.proc is not None:
                if not self.proc.is_alive():
                    self.procreport = "Finished"
                    self.proc = None
                    print("Process for {} finished".format(self.ip))
