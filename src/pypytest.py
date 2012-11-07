"""
Based on the PyPy tutorial by Andrew Brown

"""

import os
import sys
import utils.rrandom as rrandom
import utils.expr_parser as parser

# from tests import *

from engine.directives import *

try:
  from pypy.rlib import rsocket
  use_pypy = True
except:
  import socket as rsocket
  use_pypy = False
 
# copied from http://www.smipple.net/snippet/Shibukawa%20Yoshi/RPython%20echo%20server

#def parse_stuff():
#    s = '((bernoulli 0.5) (beta (bernoulli 0.5) (bernoulli 1)) (bernoulli 1) 0.03)'
#    s = '(lambda (x) (if (bernoulli x) 3.14 3))'
#    s = '(if (xor (bernoulli 1)) (+ 0 (- 5 3)) (/ 6 3))'
#    s = '(let ((x 2) (y 3) (z 4)) (* x y z))'
#    index = 0
#    (expression, index) = parser.parse_expression(s, 0)
#    print expression.__str__()

def open_socket():
    reset()

    hostip = rsocket.gethostbyname('localhost')
    if use_pypy:
      host = rsocket.INETAddress(hostip.get_host(), 5000)
      socket = rsocket.RSocket(rsocket.AF_INET, rsocket.SOCK_STREAM)
    else:
      host = (hostip, 5000)
      socket = rsocket.socket(rsocket.AF_INET, rsocket.SOCK_STREAM)
    
    socket.bind(host)
    socket.listen(1)
   
    while True:
        if use_pypy:
          (client_sock_fd, client_addr) = socket.accept()
          client_sock = rsocket.fromfd(client_sock_fd, rsocket.AF_INET, rsocket.SOCK_STREAM)
        else:
          (client_sock, client_addr) = socket.accept()
        client_sock.send("Server ready!\n")
        print 'Client contacted'
        while True:
            msg = client_sock.recv(1024)
            msg = msg.rstrip("\n")
            print "rcv: '%s'" % msg
            if msg == "exit":
                client_sock.close()
                break;
            try:
              ret_msg = parser.parse_directive(msg)
            except Exception as e:
              ret_msg = e.message
            client_sock.send(ret_msg)
        return 1

def mainloop(program, bracket_map):
    pc = 0
    tape = Tape()
    
    while pc < len(program):
      print "im in a loop"

def read(fp):
    program = ""
    while True:
        read = os.read(fp, 4096)
        if len(read) == 0:
            break
        program += read
    return program

def run(fp, niters, burnin):

    open_socket() 

    #reset()
    #
    #a = run_HMM(20, 222222, niters, burnin, True)

    #for x in a:
    #  print x.__str__(), a[x]

    #sampletimes = a[0]['TIME']
    #print average(sampletimes)
    #print standard_deviation(sampletimes)
    #
    #followtimes = a[1]['TIME']
    #print average(followtimes)
    #print standard_deviation(followtimes)

    #print sum(followtimes)

def entry_point(argv):
    #try:
    #  filename = argv[1]
    #  niters = rrandom.r_uint(int(argv[2]))
    #  burnin = rrandom.r_uint(int(argv[3]))
    #except IndexError:
    #  print "You must supply a filename"
    #  return 1

    #run(os.open(filename, os.O_RDONLY, 0777), niters, burnin)
    run(10, 10, 10)
    
    return 0

def target(*args):
    return entry_point, None
    
if __name__ == "__main__":
    entry_point(sys.argv)
