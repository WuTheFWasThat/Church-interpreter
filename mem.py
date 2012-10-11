from directives import *
from globals import EvalNode

# THIS XRP IMPLEMENTATION IS NOT INDEPENDENT OF DIRECTIVES IMPLEMENTATION 
class mem_proc_XRP(XRP):
  def __init__(self, procedure):
    self.deterministic = False
    self.procedure = procedure
    self.n = len(procedure.vars)
    self.state = {}
    self.hash = random.randint(0, 2**32-1)
  def apply(self, args = None, help = None):
    # help is call_stack if for db, is an evalnode otherwise
    assert len(args) == self.n and all([args[i].__class__.__name__ == 'Value' for i in xrange(self.n)])
    args = tuple(args)
    if globals.use_traces:
      if args not in self.state:
        evalnode = EvalNode(globals.traces, globals.traces.global_env, apply(self.procedure, args))
        evalnode.mem = True
        globals.traces.add_node(evalnode)
        self.state[args] = evalnode
      else:
        evalnode = self.state[args]
      val = evalnode.evaluate(False)
      return val
    else:
      assert type(help) == list 
      if args in self.state:
        (val, count) = self.state[args]
      else:
        val = evaluate(apply(self.procedure, args), stack = help + [-1, 'mem', hash(self.procedure), args]) 
    return val
  def incorporate(self, val, args = None, help = None):
    if globals.use_traces:
      assert help.__class__.__name__ == 'EvalNode' 
      args = tuple(args)
      assert args in self.state
      evalnode = self.state[args]
      evalnode.mem_calls.add(help)
      pass
      # TODO: we essentially assume apply has been called, and that incorporate gets called each time apply does...
    else:
      args = tuple(args)
      if args not in self.state:
        self.state[args] = (val, 1)
      else:
        (oldval, oldcount) = self.state[args]
        assert oldval == val
        self.state[args] = (oldval, oldcount + 1)
    return self.state
  def remove(self, val, args = None, help = None):
    args = tuple(args)
    assert args in self.state
    if globals.use_traces:
      assert help is not None
      evalnode = self.state[args]
      #print 
      #print self.procedure, args
      #print evalnode.expression, val, evalnode.val
      assert help in evalnode.mem_calls
      #assert val == evalnode.val
      evalnode.mem_calls.remove(help)
      if len(evalnode.mem_calls) == 0:
        evalnode.unevaluate()
    else:
      (oldval, oldcount) = self.state[args]
      assert oldval == val
      if oldcount == 1:
        del self.state[args]
      else:
        self.state[args] = (oldval, oldcount - 1)
    return self.state
  def prob(self, val, args = None):
    return 0 
  def __str__(self):
    return 'Memoization of %s XRP' % str(self.procedure)

class mem_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    self.state = {}
  def apply(self, args = None):
    assert len(args) == 1
    procedure = args[0]
    assert procedure.__class__.__name__ == 'Value' and procedure.type == 'procedure'
    if procedure not in self.state:
      mem_proc = mem_proc_XRP(procedure)
      assert mem_proc.__class__.__name__ == 'mem_proc_XRP'
      return value(mem_proc)
    # TODO: do i really want to remember?
    else:
      return self.state[procedure]
  def incorporate(self, val, args = None):
    self.state[args[0]] = val
    return self.state
  def remove(self, val, args = None):
    if args[0] in self.state:
      del self.state[args[0]]
    else:
      warnings.warn('Couldn\'t remove procedure %s from mem_XRP' % (str(args[0])))
    return self.state
  def prob(self, val, args = None):
    return 0 # correct since other flips will be added to db? 
  def __str__(self):
    return 'Memoization XRP'

mem_xrp = mem_XRP()
def mem(function):
  return expression(('apply', mem_xrp, function))

class CRP_XRP(XRP):
  def __init__(self, alpha):
    self.deterministic = False
    self.state = {}
    check_pos(alpha)
    self.alpha = alpha
    self.weight = alpha
    return
  def apply(self, args = None):
    if args != None and len(args) != 0:
      warnings.warn('Warning: CRP_XRP has no need to take in arguments %s' % str(args))
    x = random.random() * self.weight
    for id in self.state:
      x -= self.state[id]
      if x <= 0:
        return id
    return value(random.randint(0, 2**32-1))
  def incorporate(self, val, args = None):
    if args != None and len(args) != 0:
      warnings.warn('Warning: CRP_XRP has no need to take in arguments %s' % str(args))
    self.weight += 1
    if val in self.state:
      self.state[val] += 1
    else:
      self.state[val] = 1
    return self.state
  def remove(self, val, args = None):
    if args != None and len(args) != 0:
      warnings.warn('Warning: CRP_XRP has no need to take in arguments %s' % str(args))
    if val in self.state:
      if self.state[val] == 1:
        del self.state[val]
      else:
        assert self.state[val] > 1
        self.state[val] -= 1
        self.weight -= 1
    else:
      warnings.warn('Warning: CRP_XRP cannot remove the value %d, as it has state %s' % (str(val), str(self.state)))
    return self.state
  def prob(self, val, args = None):
    if args != None and len(args) != 0:
      warnings.warn('Warning: CRP_XRP has no need to take in arguments %s' % str(args))
    if val in self.state:
      return math.log(self.state[val]) - math.log(self.weight)
    else:
      return math.log(self.alpha) - math.log(self.weight)
  def __str__(self):
    return 'CRP(%f)' % (self.alpha)

class gen_CRP_XRP(XRP):
  def __init__(self):
    self.state = None
    return
  def apply(self, args = None):
    alpha = args[0].val
    check_pos(alpha)
    return Value(CRP_XRP(alpha)) 
  def incorporate(self, val, args = None):
    return None
  def remove(self, val, args = None):
    return None
  def prob(self, val, args = None):
    return 0
  def __str__(self):
    return 'CRP_XRP'

crp_xrp = gen_CRP_XRP()
def CRP(alpha):
  return expression(('apply', crp_xrp, alpha))

