# from twisted.internet import reactor, protocol
from socket import socket, AF_INET, SOCK_STREAM
import readline, os, rlcompleter, atexit, code, sys, time

# class SimToolProtocol(protocol.Protocol): 
#     def connectionMade(self):
#        self.factory.client = self
#
#    def dataReceived(self, data):
#        print data

#class SimToolClientFactory(protocol.ClientFactory):
#    protocol = SimToolProtocol
#    client = None

# class FileCacher:
#     "Cache the stdout text so we can analyze it before returning it"
#     def __init__(self): self.reset()
#     def reset(self): self.out = []
#     def write(self,line): self.out.append(line)
#     def flush(self):
#         output = '\n'.join(self.out)
#         self.reset()
#         return output

class SimtoolConsole(code.InteractiveConsole):
    def __init__(self, clt=None, locals=None, filename="<console>",
                 histfile=os.path.expanduser("~/.simtool-history")):
        code.InteractiveConsole.__init__(self, locals, filename)
        self.init_history(histfile)
        # self.stdout = sys.stdout
        # self.cache = FileCacher()
        self.client = clt
        self.buf = ''

    def init_history(self, histfile):
        readline.parse_and_bind("tab: complete")
        if hasattr(readline, "read_history_file"):
            try:
                readline.read_history_file(histfile)
            except IOError:
                pass
            atexit.register(self.save_history, histfile)

    def save_history(self, histfile):
        readline.write_history_file(histfile)

    # def get_output(self):
    #     sys.stdout = self.cache

    # def return_output(self):
    #     sys.stdout = self.stdout

    def send_cmd(self, line):
        self.client.send(line+'\r\n')

    def cmd_result(self): 
        st = time.time()
        while True:
            self.buf += self.client.recv(1024)
            bf = self.buf.split('\r\n')
            if len(bf) > 1:
                self.buf = bf[1]
                return bf[0]
            if time.time() - st > 10:
                return 'Timeout'

    def mon_show(self):
        while True:
            sys.stdout.write(self.client.recv(1024))
            time.sleep(0.5)

    def push(self, line):
        # self.get_output()
        # you can filter input here by doing something like
        # line = filter(line)
        if line == 'quit':
            self.client.close()
            code.InteractiveConsole.push(self, 'quit()')
            return
        if line[0] != '#':
            code.InteractiveConsole.push(self, line)
            return
        self.send_cmd(line[1:])
        if line == '#mon':
            self.mon_show()
        else:
            print self.cmd_result()
            code.InteractiveConsole(self,line)
        # self.return_output()
        # output = self.cache.flush()
        # you can filter the output here by doing something like
        # output = filter(output)
        # return

    def interact(self, str):
        code.InteractiveConsole.push(self, 'import base64, json\n')
        code.InteractiveConsole.push(self, 'def sdump(str): return base64.b64encode(json.dumps(str))\n')
        code.InteractiveConsole.interact(self, str)

# print help(HistoryConsole)

def main():
    toolsSck = socket(AF_INET, SOCK_STREAM)
    toolsSck.connect(('192.168.6.66', 9898))
    # toolsSck.connect(('114.215.209.188', 9898))
    # toolsSck.connect(('192.168.6.66', 9999))
    # toolsSck.connect(('localhost', 9901))
    hc = SimtoolConsole(toolsSck)
    hc.interact(hc.cmd_result())

if __name__ == "__main__":
    main()
    # stfcty = SimToolClientFactory()
    # reactor.connectTCP('192.168.6.66', 9898, stfcty)
    # reactor.run()
    # toolsSck = socket(AF_INET, SOCK_STREAM)
    # toolsSck.connect(('192.168.6.66', 9898))
    # toolsSck.connect(('114.215.209.188', 9898))
    # toolsSck.connect(('192.168.6.66', 9999))
    # toolsSck.connect(('localhost', 9901))
    
    # wel = "Simcore Tools 1.0.0 (%s)"%time.strftime("%Y-%m-%d %H:%M:%S")
    # hc = SimtoolConsole(toolsSck)
    # hc.interact(hc.cmd_result())
