from socket import socket, AF_INET, SOCK_STREAM
import base64, json, time, sys, msgpack, struct
import nacl.utils, nacl.secret, nacl.public

class User(dict):
    def __init__(self, id, info, core):
        self.id = id
        self.core = core
        self.update(info)

    def monitor(self):
        self.core.sendCmd('mon', [self.id])
        self.core.recvMonitor()
        # self.core.send_cmd('mon', [self.id])
        # self.core.monitor()

class Chip(dict):
    def __init__(self, id, info, core):
        self.id = id
        self.core = core
        self.update(info)

    def at6(self, cmd):
        self.core.sendCmd('cmd', [self['sid'], 1001, [self.id, 6, '0', 0x00, 5, 'AT+<6>\r', cmd]])
        self.core.recvChipCmd()
        # self.core.send_cmd('cmd', [self['sid'], 1001, [self.id, 6, '0', 0x00, 5, 'AT+<6>\r', cmd]])
        # self.core.chip_cmd_result()

    def monitor(self):
        self.core.sendCmd('mon', [self.id])
        self.core.recvMonitor()
        # self.core.send_cmd('mon', [self.id])
        # self.core.monitor()

class PackBase(object):
    # Package struct implement Hub Protocol 

    _headerSync = '\x05\x00\x0B\x00'
    _version = 1
    _headerLen = 14

    def dump(self):
        # Dump the package to bytes.
        #   Will generate a new session id if self.sid is None. 

        bodyPacked = msgpack.packb(self.body) if self.body != None else ""
        sidPacked = '' if self.sid == None else uuid.UUID(hex=self.sid).bytes
        header = struct.pack("!4sccHHc3s", self._headerSync, chr(self._version), chr(self._flags), self.apiRet, self.id, chr(len(sidPacked)), struct.pack("!I", len(bodyPacked))[1:])
        return header + sidPacked + bodyPacked

    def __init__(self, id, apiRet, sid, body):
        # @param id:          Package id, unique in socket.
        # @param apiRet:      Route code to match the route api in Request package, Route return code in Respond package
        # @param sid:         Session id
        # @param body:        Package body, should be array or hash

        self.id, self.apiRet, self.sid, self.body  = id, apiRet, sid, body
        self.routeCode = None
        self._TPack = None
        self._PPack = None

    def length(self):
        sidLen = 0 if self.sid == '' else len(uuid.UUID(hex=self.sid).bytes)
        return self._headerLen + sidLen + len(msgpack.packb(self.body) if self.body != None else "")

class TPack(PackBase):
    # Request Package inherit from PackBase
    #   See Wiki for more: http://192.168.6.66/projects/sim/wiki/Hub%E5%8D%8F%E8%AE%AE

    _flags = 0x00

    def __init__(self, id, apiRet, sid, body):
        PackBase.__init__(self, id, apiRet, sid, body)
        self.routeCode = apiRet

    def peerToPPack(self, pp):
        self._PPack = pp
        return self

class DPack(PackBase):
    # Respond Package inherit from PackBase
    #   See Wiki for more: http://192.168.6.66/projects/sim/wiki/Hub%E5%8D%8F%E8%AE%AE

    _flags = 0x80

    def peerToTPack(self, tp):
        self._TPack = tp
        self.routeCode = tp.routeCode
        self._PPack = tp._PPack
        return self

class SimToolSck():
    def __init__(self):
        self.start()
        self.pubBox = nacl.public.Box(nacl.public.PrivateKey('~\xa6\xdc5QN\x03\xcf\xfa=\xb1!\xc1\xf6\xdd\x98\x7f\x98\x83[\x86<\xe8\xf3-<2\x87\xbc\xfd\x18\x96'), nacl.public.PublicKey('l30\xc8\xa2\x01g\xb2\x99\x11\xe1\xab\xd2H\xc7\x90\x12+\xcdAQ\xa9`\xfb\xd1\x0ce2\xc9\x95\xbdl'))
        self.key = self.recvPlain()
        self.box = nacl.secret.SecretBox(self.key)
        self.sendCmd('wel')
        print self.recvCmd()
        # self.sck.connect(('114.215.209.188', 9898))

    def start(self):
        self.buf = ''
        self.addr = ('192.168.6.66', 9898)
        # self.addr = ('114.215.209.188', 9898)
        # self.addr = ('115.29.241.227', 9898)
        self.sck = socket(AF_INET, SOCK_STREAM)
        self.sck.connect(self.addr)

    def test(self):
        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        self.sck.send(self.box.encrypt('test', nonce)+'\r\n')
        print self.recvPlain()

    def sendCmd(self, cmd, args=None):
        nonce = nacl.utils.random(nacl.secret.SecretBox.NONCE_SIZE)
        self.sck.send(self.box.encrypt(msgpack.packb([cmd, args]), nonce)+'\r\n')

    def recvPlain(self):
        st = time.time()
        while True:
            lines = (self.buf + self.sck.recv(1024)).split('\r\n')
            self.buf = lines.pop(-1)
            if len(lines) > 0:
                return self.pubBox.decrypt(lines[0])
            if time.time() - st > 10:
                return 'Timeout'

    def recvCmd(self):
        st = time.time()
        while True:
            lines = (self.buf + self.sck.recv(1024)).split('\r\n')
            self.buf = lines.pop(-1)
            if len(lines) > 0:
                return msgpack.unpackb(self.box.decrypt(lines[0]))
            if time.time() - st > 10:
                return 'Timeout'

    def recvChipCmd(self):
        st = time.time()
        ln = 0
        while True:
            now = time.strftime("%m-%d %H:%M:%S")
            lines = (self.buf + self.sck.recv(1024)).split('\r\n')
            self.buf = lines.pop(-1)
            for line in lines:
                if line == '': continue
                ln += 1
                for l in msgpack.unpackb(self.box.decrypt(line), encoding = 'utf-8').split('\n'):
                    print now, l
            if ln > 1: return
            if time.time() - st > 10:
                print 'Timeout'
                return

    def recvMonitor(self):
        try:
            while True:
                now = time.strftime("%m-%d %H:%M:%S")
                lines = (self.buf + self.sck.recv(1024)).split('\r\n')
                self.buf = lines.pop(-1)
                for line in lines:
                    if line == '': continue
                    try:
                        for l in msgpack.unpackb(self.box.decrypt(line), encoding = 'utf-8').split('\n'): print now, l
                    except:
                        pass
                time.sleep(0.5)
        except KeyboardInterrupt, e:
            # self.send_cmd('monstop')
            self.sendCmd('monstop')
            time.sleep(0.5)
            self.sck.recv(20480)
            self.buf = ''

    def dumpT(self, pid, apiRet, body):
        return TPack(pid, apiRet, None, body).dump()

    def dumpD(self, pid, apiRet, body):
        return DPack(pid, apiRet, None, body).dump()

    def packLoads(buf):
    # Load TPack or DPack from socket buffer
    #   return remaining buffer and parsed Pack
    #   -*- TODO -*- : Make it into SHProtocol class, global method is not good

        if len(buf) < 4: return buf, None

        idx = buf.find(PackBase._headerSync)
        if idx < 0:
            print "no header_sync, drop", len(buf)-3
            return buf[-3:], None
        elif idx > 0:
            print "some noise before header_sync, drop", idx
            buf = buf[idx:]

        if len(buf) < PackBase._headerLen: return buf, None

        sync, ver, flags, apiRet, packid, sidLen, bodyLen = struct.unpack("!4sccHHc3s", buf[:PackBase._headerLen])
        ver = ord(ver)
        flags = ord(flags)
        sidLen = ord(sidLen)
        bodyLen, = struct.unpack("!I",'\x00'+bodyLen)

        if ver == PackBase._version and (flags & 0xffffff3f) == 0 and (sidLen == 0 or sidLen == 16) : pass
        else:
            print "header check error, drop", 1
            return buf[1:], None

        pkgLen = PackBase._headerLen + sidLen + bodyLen
        if len(buf) < pkgLen: return buf, None
        elif len(buf) > pkgLen:
            if not buf[pkgLen:].startswith(PackBase._headerSync[:len(buf)-pkgLen]):
                print "header_sync after body check error, drop", 1
                return buf[1:], None

        sid = buf[PackBase._headerLen : PackBase._headerLen+sidLen]
        if sidLen == 16: sid = uuid.UUID(bytes=sid).hex
        bodyStr  = buf[PackBase._headerLen+sidLen : pkgLen]

        if len(bodyStr) == 0: body = None
        else:
            try:
                body = msgpack.unpackb(bodyStr, encoding = 'utf-8')
            except Exception, e:
                print "body decode error, drop", pkgLen
                return buf[pkgLen:], None

        pack = TPack(packid, apiRet, sid, body) if flags == 0x00 else DPack(packid, apiRet, sid, body)
        
        return pack


######################################################################        

    # def send_cmd(self, cmd, args=None):
    #     self.sck.send(base64.b64encode(json.dumps([cmd, args]))+'\r\n')

    # def cmd_result(self):
    #     st = time.time()
    #     while True:
    #         lines = (self.buf + self.sck.recv(1024)).split('\r\n')
    #         self.buf = lines.pop(-1)
    #         if len(lines) > 0:
    #             return base64.b64decode(lines[0])
    #         if time.time() - st > 10:
    #             return 'Timeout'

    # def chip_cmd_result(self):
    #     st = time.time()
    #     ln = 0
    #     while True:
    #         now = time.strftime("%m-%d %H:%M:%S")
    #         lines = (self.buf + self.sck.recv(1024)).split('\r\n')
    #         self.buf = lines.pop(-1)
    #         for line in lines:
    #             if line == '': continue
    #             ln += 1
    #             for l in msgpack.unpackb(line, encoding = 'utf-8').split('\n'):
    #                 print now, l
    #         if ln > 1: return
    #         if time.time() - st > 10:
    #             print 'Timeout'
    #             return

    # def monitor(self):
    #     try:
    #         while True:
    #             now = time.strftime("%m-%d %H:%M:%S")
    #             lines = (self.buf + self.sck.recv(1024)).split('\r\n')
    #             self.buf = lines.pop(-1)
    #             for line in lines:
    #                 if line == '': continue
    #                 try:
    #                     for l in msgpack.unpackb(line, encoding = 'utf-8').split('\n'): print now, l
    #                 except:
    #                     pass
    #             time.sleep(0.5)
    #     except KeyboardInterrupt, e:
    #         self.send_cmd('monstop')
    #         time.sleep(0.5)
    #         self.sck.recv(20480)
    #         self.buf = ''

    def mon(self, mos):
        self.sendCmd('mon', [ m.id for m in mos ])
        self.recvMonitor()
        # self.send_cmd('mon', [ m.id for m in mos ])
        # self.monitor()

    def monall(self):
        self.sendCmd('monall')
        self.recvMonitor()
        # self.send_cmd('monall')
        # self.monitor()

    def chip(self, id):
        self.sendCmd('chip', id)
        info = self.recvCmd()
        # self.send_cmd('chip', id)
        # info = json.loads(self.cmd_result())
        return Chip(id, info, self)

    def user(self, id):
        self.sendCmd('user', id)
        info = self.recvCmd()
        # self.send_cmd('user', id)
        # info = json.loads(self.cmd_result())
        if not info: 
            print 'No User %s'%id
            return
        return User(id, info, self)

    def boxes(self):
        self.sendCmd('boxes')
        sts = self.recvCmd()
        # self.send_cmd('boxes')
        # sts = self.cmd_result()
        print sts

    def sockets(self):
        self.sendCmd('sockets')
        sts = self.recvCmd()
        print sts

    def close(self):
        self.sck.close()
        self.sck = None

    # def sdump(self, str): 
    #     return base64.b64encode(json.dumps(str))
