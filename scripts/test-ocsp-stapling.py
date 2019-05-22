# Author: Hubert Kario, (c) 2016
# Released under Gnu GPL v2.0, see LICENSE file for details

from __future__ import print_function
import traceback
import sys
import getopt
import re
from itertools import chain

from tlsfuzzer.runner import Runner
from tlsfuzzer.messages import Connect, ClientHelloGenerator, \
        ClientKeyExchangeGenerator, ChangeCipherSpecGenerator, \
        FinishedGenerator, ApplicationDataGenerator, AlertGenerator, \
        ResetHandshakeHashes
from tlsfuzzer.expect import ExpectServerHello, ExpectCertificate, \
        ExpectServerHelloDone, ExpectChangeCipherSpec, ExpectFinished, \
        ExpectAlert, ExpectApplicationData, ExpectClose, \
        ExpectCertificateStatus

from tlslite.constants import CipherSuite, AlertLevel, AlertDescription, \
        ExtensionType
from tlslite.extensions import StatusRequestExtension


def natural_sort_keys(s, _nsre=re.compile('([0-9]+)')):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(_nsre, s)]


def help_msg():
    print("Usage: <script-name> [-h hostname] [-p port] [[probe-name] ...]")
    print(" -h hostname    name of the host to run the test against")
    print("                localhost by default")
    print(" -p port        port number to use for connection, 4433 by default")
    print(" probe-name     if present, will run only the probes with given")
    print("                names and not all of them, e.g \"sanity\"")
    print(" -e probe-name  exclude the probe from the list of the ones run")
    print("                may be specified multiple times")
    print(" -r number      renegotiate in the connection given number of "
          "times")
    print("                1 by default")
    print(" --no-status    don't expect ocsp to be supported")
    print(" --help         this message")


def main():
    host = "localhost"
    port = 4433
    run_exclude = set()
    renego = 1
    status = True

    argv = sys.argv[1:]
    opts, args = getopt.getopt(argv, "h:p:e:r:", ["help", "no-status"])
    for opt, arg in opts:
        if opt == '-h':
            host = arg
        elif opt == '-p':
            port = int(arg)
        elif opt == '-e':
            run_exclude.add(arg)
        elif opt == '-r':
            renego = int(arg)
        elif opt == '--no-status':
            status = False
        elif opt == '--help':
            help_msg()
            sys.exit(0)
        else:
            raise ValueError("Unknown option: {0}".format(opt))

    if args:
        run_only = set(args)
    else:
        run_only = None

    conversations = {}

    # check if status_request is recognized and supported
    conversation = Connect(host, port)
    node = conversation
    ciphers = [CipherSuite.TLS_RSA_WITH_AES_128_CBC_SHA,
               CipherSuite.TLS_EMPTY_RENEGOTIATION_INFO_SCSV]
    ocsp = StatusRequestExtension().create()
    ext = {ExtensionType.status_request: ocsp}
    node = node.add_child(ClientHelloGenerator(ciphers, extensions=ext))
    ext_srv = {ExtensionType.renegotiation_info: None}
    if status:
        ext_srv[ExtensionType.status_request] = None
    node = node.add_child(ExpectServerHello(extensions=ext_srv))
    node = node.add_child(ExpectCertificate())
    if status:
        node = node.add_child(ExpectCertificateStatus())
    node = node.add_child(ExpectServerHelloDone())
    node = node.add_child(ClientKeyExchangeGenerator())
    node = node.add_child(ChangeCipherSpecGenerator())
    node = node.add_child(FinishedGenerator())
    node = node.add_child(ExpectChangeCipherSpec())
    node = node.add_child(ExpectFinished())
    node = node.add_child(ApplicationDataGenerator(
        bytearray(b"GET / HTTP/1.0\n\n")))
    node = node.add_child(ExpectApplicationData())
    node = node.add_child(AlertGenerator(AlertLevel.warning,
                                         AlertDescription.close_notify))
    node = node.add_child(ExpectAlert())
    node.next_sibling = ExpectClose()
    conversations["sanity"] = conversation

    # check if status_request is recognized and supported
    conversation = Connect(host, port)
    node = conversation
    ciphers = [CipherSuite.TLS_RSA_WITH_AES_128_CBC_SHA,
               CipherSuite.TLS_EMPTY_RENEGOTIATION_INFO_SCSV]
    ocsp = StatusRequestExtension().create()
    ext = {ExtensionType.status_request: ocsp}
    node = node.add_child(ClientHelloGenerator(ciphers, extensions=ext))
    ext_srv = {ExtensionType.renegotiation_info: None}
    if status:
        ext_srv[ExtensionType.status_request] = None
    node = node.add_child(ExpectServerHello(extensions=ext_srv))
    node = node.add_child(ExpectCertificate())
    if status:
        node = node.add_child(ExpectCertificateStatus())
    node = node.add_child(ExpectServerHelloDone())
    node = node.add_child(ClientKeyExchangeGenerator())
    node = node.add_child(ChangeCipherSpecGenerator())
    node = node.add_child(FinishedGenerator())
    node = node.add_child(ExpectChangeCipherSpec())
    node = node.add_child(ExpectFinished())
    ciphers = [CipherSuite.TLS_RSA_WITH_AES_128_CBC_SHA]
    ext = {ExtensionType.status_request: ocsp,
           ExtensionType.renegotiation_info: None}
    # renegotiate
    node = node.add_child(ResetHandshakeHashes())
    node = node.add_child(ClientHelloGenerator(ciphers, extensions=ext,
                                               session_id=bytearray()))
    node = node.add_child(ExpectServerHello(extensions=ext_srv))
    node = node.add_child(ExpectCertificate())
    if status:
        node = node.add_child(ExpectCertificateStatus())
    node = node.add_child(ExpectServerHelloDone())
    node = node.add_child(ClientKeyExchangeGenerator())
    node = node.add_child(ChangeCipherSpecGenerator())
    node = node.add_child(FinishedGenerator())
    node = node.add_child(ExpectChangeCipherSpec())
    node = node.add_child(ExpectFinished())
    #node = node.add_child(ApplicationDataGenerator(
    #    bytearray(b"GET / HTTP/1.0\n\n")))
    #node = node.add_child(ExpectApplicationData())
    node = node.add_child(AlertGenerator(AlertLevel.warning,
                                         AlertDescription.close_notify))
    node = node.add_child(ExpectAlert())
    node.next_sibling = ExpectClose()
    conversations["renegotiate"] = conversation

    # check if responder_id_list is supported
    conversation = Connect(host, port)
    node = conversation
    ciphers = [CipherSuite.TLS_RSA_WITH_AES_128_CBC_SHA,
               CipherSuite.TLS_EMPTY_RENEGOTIATION_INFO_SCSV]
                                                              # DER encoding of CHOICE[1] OCTETSTRING (20)
    ocsp = StatusRequestExtension().create(responder_id_list=[bytearray(b'\xa2\x16\x04\x14') + bytearray([(i+2) % 256]*20) for i in range(625)])
    ocsp.responder_id_list += [bytearray(b'\xa2\x16\x04\x14') + bytearray(b'\x18\x70\x95\x0B\xE0\x8E\x49\x98\x76\x23\x54\xE7\xD1\xFB\x4E\x9B\xB6\x67\x5E\x2B')]
    ext = {ExtensionType.status_request: ocsp}
    node = node.add_child(ClientHelloGenerator(ciphers, extensions=ext))
    ext_srv = {ExtensionType.renegotiation_info: None}
    if status:
        ext_srv[ExtensionType.status_request] = None
    node = node.add_child(ExpectServerHello(extensions=ext_srv))
    node = node.add_child(ExpectCertificate())
    if status:
        node = node.add_child(ExpectCertificateStatus())
    node = node.add_child(ExpectServerHelloDone())
    node = node.add_child(ClientKeyExchangeGenerator())
    node = node.add_child(ChangeCipherSpecGenerator())
    node = node.add_child(FinishedGenerator())
    node = node.add_child(ExpectChangeCipherSpec())
    node = node.add_child(ExpectFinished())
    ciphers = [CipherSuite.TLS_RSA_WITH_AES_128_CBC_SHA]
    ext = {ExtensionType.status_request: ocsp,
           ExtensionType.renegotiation_info: None}
    # renegotiate
    for _ in range(renego):
        node = node.add_child(ResetHandshakeHashes())
        node = node.add_child(ClientHelloGenerator(ciphers, extensions=ext,
                                                   session_id=bytearray()))
        node = node.add_child(ExpectServerHello(extensions=ext_srv))
        node = node.add_child(ExpectCertificate())
        if status:
            node = node.add_child(ExpectCertificateStatus())
        node = node.add_child(ExpectServerHelloDone())
        node = node.add_child(ClientKeyExchangeGenerator())
        node = node.add_child(ChangeCipherSpecGenerator())
        node = node.add_child(FinishedGenerator())
        node = node.add_child(ExpectChangeCipherSpec())
        node = node.add_child(ExpectFinished())
    #node = node.add_child(ApplicationDataGenerator(
    #    bytearray(b"GET / HTTP/1.0\n\n")))
    #node = node.add_child(ExpectApplicationData())
    node = node.add_child(AlertGenerator(AlertLevel.warning,
                                         AlertDescription.close_notify))
    node = node.add_child(ExpectAlert())
    node.next_sibling = ExpectClose()
    conversations["renegotiate with large responder_id_list"] = conversation

    # run the conversation
    good = 0
    bad = 0
    failed = []

    # make sure that sanity test is run first and last
    # to verify that server was running and kept running throughout
    sanity_tests = [('sanity', conversations['sanity'])]
    ordered_tests = chain(sanity_tests,
                          filter(lambda x: x[0] != 'sanity',
                                 conversations.items()),
                          sanity_tests)

    for c_name, c_test in ordered_tests:
        if run_only and c_name not in run_only or c_name in run_exclude:
            continue
        print("{0} ...".format(c_name))

        runner = Runner(c_test)

        res = True
        try:
            runner.run()
        except:
            print("Error while processing")
            print(traceback.format_exc())
            res = False

        if res:
            good+=1
            print("OK")
        else:
            bad+=1
            failed.append(c_name)

    print("Test end")
    print("successful: {0}".format(good))
    print("failed: {0}".format(bad))
    failed_sorted = sorted(failed, key=natural_sort_keys)
    print("  {0}".format('\n  '.join(repr(i) for i in failed_sorted)))

    if bad > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
