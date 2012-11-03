from globals import EvalNode
import globals
from expressions import *

# THIS XRP IMPLEMENTATION IS NOT INDEPENDENT OF DIRECTIVES IMPLEMENTATION 
class mem_proc_XRP(XRP):
  def __init__(self, procedure):
    self.deterministic = False
    self.procedure = procedure
    self.n = len(procedure.vars)
    self.state = {}
    self.hash = rrandom.random.randint()
  def apply(self, args = None, help = None):
    assert len(args) == self.n
    args = tuple(args)
    if globals.use_traces:
      if args not in self.state:
        evalnode = EvalNode(globals.traces, globals.traces.env, ApplyExpression(ConstExpression(self.procedure), [ConstExpression(arg) for arg in args]))
        evalnode.mem = True
        globals.traces.add_node(evalnode)
        self.state[args] = evalnode
      else:
        evalnode = self.state[args]
      val = evalnode.evaluate(False)
      return val
    else:
      # help is call_stack for db
      if args in self.state:
        (val, count) = self.state[args]
      else:
        val = globals.db.evaluate(ApplyEpxression(ConstExpression(self.procedure), [ConstExpression(arg) for arg in args]), stack = help + [-1, 'mem', self.procedure.hash, ','.join([str(x) for x in args])]) 
    return val
  def incorporate(self, val, args = None, help = None):
    if globals.use_traces:
      # help is evalnode
      assert help.__class__.__name__ == 'EvalNode' 
      args = tuple(args)
      assert args in self.state
      evalnode = self.state[args]
      assert help not in evalnode.mem_calls
      evalnode.mem_calls[help] = True
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
      assert help in evalnode.mem_calls
      del evalnode.mem_calls[help]
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
    assert procedure.type == 'procedure'
    mem_proc = mem_proc_XRP(procedure)
    return XRPValue(mem_proc)
  def incorporate(self, val, args = None):
    assert val.type == 'xrp'
    assert val.xrp not in self.state
    self.state[val.xrp] = args[0]
    return self.state
  def remove(self, val, args = None):
    assert val.type == 'xrp'
    assert val.xrp in self.state
    # unevaluate val's evalnodes
    if globals.use_traces:
      for args in val.xrp.state:
        evalnode = val.xrp.state[args]
        evalnode.unevaluate()
    del self.state[val.xrp]
    return self.state
  def prob(self, val, args = None):
    return 0 # correct since other flips will be added to db? 
  def __str__(self):
    return 'Memoization XRP'

mem_xrp = ConstExpression(XRPValue(mem_XRP()))
def mem(function):
  return ApplyExpression(mem_xrp, [function])

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
    x = rrandom.random.random() * self.weight
    for id in self.state:
      x -= self.state[id]
      if x <= 0:
        return id
    return NumValue(rrandom.random.randint())
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
    alpha = args[0].num
    check_pos(alpha)
    return XRPValue(CRP_XRP(alpha)) 
  def incorporate(self, val, args = None):
    return None
  def remove(self, val, args = None):
    return None
  def prob(self, val, args = None):
    return 0
  def __str__(self):
    return 'CRP_XRP'

crp_xrp = ConstExpression(XRPValue(gen_CRP_XRP()))
def CRP(alpha):
  return ApplyExpression(crp_xrp, alpha)

