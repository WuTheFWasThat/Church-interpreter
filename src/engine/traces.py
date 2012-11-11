from engine import *
from expressions import *
from environment import *
from utils.random_choice_dict import RandomChoiceDict

try:
  from pypy.rlib.jit import JitDriver
  jitdriver = JitDriver(greens = [], reds=['node'])
  
  def jitpolicy(driver):
    from pypy.jit.codewriter.policy import JitPolicy
    return JitPolicy()

  use_jit = True
except:
  use_jit = False

# THEN, in REFLIP:

# Class representing environments
class EnvironmentNode(Environment):
  def __init__(self, parent = None):
    self.parent = parent # The parent environment
    self.assignments = {} # Dictionary from names to values

    self.assumes = {}
    self.lookups = {} # just a set
    return

  def add_assume(self, name, evalnode):
    if name in self.assumes:
      raise Exception("Already assumed something with this name")
    self.assumes[name] = evalnode

  def add_lookup(self, name, evalnode):
    if name not in self.lookups:
      self.lookups[name] = {}
    self.lookups[name][evalnode] = True

  def rem_lookup(self, name, evalnode):
    del self.lookups[name][evalnode]

  def get_lookups(self, name, evalnode):
    if self.assumes[name] is not evalnode:
      raise Exception("Wrong evalnode getting lookups for %s" % name)
    if name in self.lookups:
      return self.lookups[name]
    else:
      return {}

  def spawn_child(self): 
    return EnvironmentNode(self)

class EvalNode:
  def __init__(self, traces, env, expression):
    self.traces = traces

    self.active = False # Whether this node is currently activated

    self.parent = None 
    self.children = {} 
    self.applychildren = {} 

    self.mem = False # Whether this is the root of a mem'd procedure's application
    self.mem_calls = {} # just a set

    self.env = env # Environment in which this was evaluated
    self.lookup = None 
    self.assume = False
    self.assume_name = None

    self.observed = False
    self.observe_val = None 

    self.xrp = XRP()
    self.xrp_apply = False
    self.random_xrp_apply = False
    self.procedure_apply = False
    self.args = None
    self.p = 0

    self.expression = expression
    self.type = expression.type

    self.val = None
    return

  def get_child(self, addition, env, subexpr, is_apply = False):
    children = (self.applychildren if is_apply else self.children)

    if addition not in children:
      self.spawnchild(addition, env, subexpr, is_apply)
    evalnode = children[addition]
    evalnode.env = env
    return evalnode
  
  def spawnchild(self, addition, env, subexpr, is_apply = False):
    child = EvalNode(self.traces, env, subexpr)
    child.parent = self
    if is_apply:
      self.applychildren[addition] = child
    else:
      self.children[addition] = child

  def add_assume(self, name, env):
    assert env == self.env
    self.assume_name = name
    self.assume = True

  def observe(self, obs_val):
    self.observed = True
    self.observe_val = obs_val

  def setlookup(self, env):
    assert self.expression.type == 'variable'
    self.lookup = env 
    env.add_lookup(self.expression.name, self)

  def remlookup(self, name, env):
    self.lookup = None
    env.rem_lookup(name, self)

  def setargs(self, args):
    assert self.type == 'apply'
    self.args = args

  def propogate_up(self, start = False):
    # NOTE: 
    # assert self.active <--- almost true
    # This only breaks when this node is unevaluated from another branch of propogate_up
    # but this means children may have changed, so if we activate this branch and don't re-evaluate,
    # the result may be wrong!  We can't always re-evaluate the branches, because of the way reflip restores.
    # TODO: optimize to not re-propogate. needs to calculate explicit trace structure

    if self.random_xrp_apply:
      if not start:
        oldval = self.val
        val = self.evaluate(reflip = 0.5, xrp_force_val = self.val)
        assert val == oldval
        return val
      else:
        val = self.val
    else:
      val = self.evaluate(reflip = 0.5, xrp_force_val = None)

    if self.assume:
      assert self.parent is None
      # lookups can be affected *while* propogating up. 
      lookup_nodes = []
      for evalnode in self.env.get_lookups(self.assume_name, self):
        lookup_nodes.append(evalnode)
      for evalnode in lookup_nodes:
        evalnode.propogate_up()
    elif self.parent is not None:
      self.parent.propogate_up()

    if self.mem:
      # self.mem_calls can be affected *while* propogating up.  However, if new links are created, they'll use the new value
      for evalnode in self.mem_calls.keys():
        evalnode.propogate_up()

    self.val = val
    return self.val

  def unevaluate(self):
    # NOTE:  We may want to remove references to nodes when we unevaluate, such as when we have arguments
    # drawn from some continuous domain
    if not self.active:
      return
    expr = self.expression
    if self.type == 'variable':
      # Don't remove reference value.
      assert self.lookup
      self.remlookup(expr.name, self.lookup)
    elif self.type == 'apply':
      n = len(expr.children)
      for i in range(n):
        self.get_child('arg' + str(i), self.env, expr.children[i]).unevaluate()
      self.get_child('operator', self.env, expr.op).unevaluate()
      if self.procedure_apply: 
        addition = ','.join([x.str_hash for x in self.args])
        assert addition in self.applychildren
        self.applychildren[addition].unevaluate()
      else:
        assert self.xrp_apply
        self.remove_xrp()
    else:
      for x in self.children:
        self.children[x].unevaluate()

    self.active = False
    return

  def remove_xrp(self):
    assert self.active
    xrp = self.xrp
    args = self.args
    if xrp.is_mem():
      xrp.remove_mem(self.val, args, self)
    else:
      xrp.remove(self.val, args)
    prob = xrp.prob(self.val, self.args)
    self.traces.uneval_p += prob
    self.traces.p -= prob
    if not xrp.deterministic:
      self.traces.remove_xrp(self)

  def add_xrp(self, xrp, val, args):
    prob = xrp.prob(val, args)
    self.p = prob
    self.traces.eval_p += prob
    self.traces.p += prob
    if xrp.is_mem():
      xrp.incorporate_mem(val, args, self)
    else:
      xrp.incorporate(val, args)

    if not xrp.deterministic:
      self.random_xrp_apply = True
      self.traces.add_xrp(args, self)

  def evaluate_recurse(self, subexpr, env, addition, reflip, is_apply = False):
    child = self.get_child(addition, env, subexpr, is_apply)
    val = child.evaluate(reflip == True)
    return val
  
  def binary_op_evaluate(self, reflip):
    val1 = self.evaluate_recurse(self.expression.children[0], self.env, 'operand0', reflip)
    val2 = self.evaluate_recurse(self.expression.children[1], self.env, 'operand1', reflip)
    return (val1 , val2)

  def children_evaluate(self, reflip):
    return [self.evaluate_recurse(self.expression.children[i], self.env, 'child' + str(i), reflip) for i in range(len(self.expression.children))]
  
  # reflip = 1 # reflip all
  #          0.5 # reflip current, but don't recurse
  #          0 # reflip nothing
  def evaluate(self, reflip = False, xrp_force_val = None):
    if reflip == False and self.active:
      assert self.val is not None
      return self.val

    expr = self.expression

    if self.observed:
      xrp_force_val = self.observe_val

    if xrp_force_val is not None:
      if self.type != 'apply':
        raise Exception("Require outermost XRP application")

    if self.type == 'value':
      val = expr.val
    elif self.type == 'variable':
      (val, lookup_env) = self.env.lookup(expr.name)
      self.setlookup(lookup_env)
    elif self.type == 'if':
      cond = self.evaluate_recurse(expr.cond, self.env, 'cond', reflip)
      if cond.bool:
        self.get_child('false', self.env, expr.false).unevaluate()
        val = self.evaluate_recurse(expr.true, self.env, 'true', reflip)
      else:
        self.get_child('true', self.env, expr.true).unevaluate()
        val = self.evaluate_recurse(expr.false, self.env, 'false', reflip)
    #elif self.type == 'switch':
    #  index = self.evaluate_recurse(expr.index, self.env, 'index', reflip)
    #  assert 0 <= index.num < expr.n
    #  for i in range(expr.n):
    #    if i != index.num:
    #      self.get_child('child' + str(i), self.env, expr.children[i]).unevaluate()
    #  val = self.evaluate_recurse(self.children[index.num] , self.env, 'child' + str(index.num), reflip)
    elif self.type == 'let':
      # TODO: this really is a let*
      n = len(expr.vars)
      assert len(expr.expressions) == n
      values = []
      new_env = self.env
      for i in range(n): # Bind variables
        new_env = new_env.spawn_child()
        val = self.evaluate_recurse(expr.expressions[i], new_env, 'let' + str(i), reflip)
        values.append(val)
        new_env.set(expr.vars[i], values[i])
        if val.type == 'procedure':
          val.env = new_env
      new_body = expr.body.replace(new_env)
      # TODO :  should probably be an applychild
      self.get_child('letbody', new_env, new_body).unevaluate()
      val = self.evaluate_recurse(new_body, new_env, 'letbody', reflip)

    elif self.type == 'apply':
      n = len(expr.children)
      args = [self.evaluate_recurse(expr.children[i], self.env, 'arg' + str(i), reflip) for i in range(n)]
      op = self.evaluate_recurse(expr.op, self.env, 'operator', reflip)

      if xrp_force_val is not None:
        if op.type != 'xrp':
          raise Exception("Require outermost XRP application")

      if op.type == 'procedure':
        self.procedure_apply = True
        for x in self.applychildren:
          self.applychildren[x].unevaluate()

        if n != len(op.vars):
          raise Exception('Procedure should have %d arguments.  \nVars were \n%s\n, but had %d children.' % (n, op.vars, len(expr.children)))
        new_env = op.env.spawn_child()
        for i in range(n):
          new_env.set(op.vars[i], args[i])
        addition = ','.join([x.str_hash for x in args])
        val = self.evaluate_recurse(op.body, new_env, addition, reflip, True)
      elif op.type == 'xrp':
        self.xrp_apply = True
        xrp = op.xrp

        if reflip == False and self.val is not None: # also inactive
          val = self.val
          self.add_xrp(self.xrp, self.val, self.args)
        elif xrp_force_val is not None:
          assert reflip != True or self.observed
          if xrp.deterministic:
            raise Exception("Forced XRP application should not be deterministic")
            
          val = xrp_force_val
          if self.active:
            self.remove_xrp()
          self.add_xrp(xrp, val, args)

        elif xrp.deterministic or (not reflip):
          if self.active:
            if self.args == args and self.xrp == xrp:
              val = self.val
            else:
              self.remove_xrp()
              val = xrp.apply(args)
              self.add_xrp(xrp, val, args)
          else:
            val = xrp.apply(args)
            self.add_xrp(xrp, val, args)
        else: # not deterministic, needs reflipping
          if self.active:
            self.remove_xrp()
          val = xrp.apply(args)
          self.add_xrp(xrp, val, args)

        self.xrp = xrp
        assert val is not None
      else:
        raise Exception('Must apply either a procedure or xrp.  Instead got expression %s' % str(op))

      self.args = args
    elif self.type == 'function':
      n = len(expr.vars)
      new_env = self.env.spawn_child()
      bound = {}
      for i in range(n): # Bind variables
        bound[expr.vars[i]] = True
      procedure_body = expr.body.replace(new_env, bound)
      val = Procedure(expr.vars, procedure_body, self.env)
    elif self.type == '=':
      (val1, val2) = self.binary_op_evaluate(reflip)
      val = val1.__eq__(val2)
    elif self.type == '<':
      (val1, val2) = self.binary_op_evaluate(reflip)
      val = val1.__lt__(val2)
    elif self.type == '>':
      (val1, val2) = self.binary_op_evaluate(reflip)
      val = val1.__gt__(val2)
    elif self.type == '<=':
      (val1, val2) = self.binary_op_evaluate(reflip)
      val = val1.__le__(val2)
    elif self.type == '>=':
      (val1, val2) = self.binary_op_evaluate(reflip)
      val = val1.__ge__(val2)
    elif self.type == '&':
      vals = self.children_evaluate(reflip)
      andval = BoolValue(True)
      for x in vals:
        andval = andval.__and__(x.bool)
      val = andval
    elif self.type == '^':
      vals = self.children_evaluate(reflip)
      xorval = BoolValue(True)
      for x in vals:
        xorval = xorval.__xor__(x.bool)
      val = xorval
    elif self.type == '|':
      vals = self.children_evaluate(reflip)
      orval = BoolValue(False)
      for x in vals:
        orval = orval.__or__(x.bool)
      val = orval
    elif self.type == '~':
      negval = self.evaluate_recurse(expr.children[0] , self.env, 'neg', reflip)
      val = negval.__inv__()
    elif self.type == '+':
      vals = self.children_evaluate(reflip)
      sum_val = NatValue(0)
      for x in vals:
        sum_val = sum_val.__add__(x)
      val = sum_val
    elif self.type == '-':
      val1 = self.evaluate_recurse(expr.children[0] , self.env, 'sub0', reflip)
      val2 = self.evaluate_recurse(expr.children[1] , self.env, 'sub1', reflip)
      val = val1.__sub__(val2)
    elif self.type == '*':
      vals = self.children_evaluate(reflip)
      prod_val = NatValue(1)
      for x in vals:
        prod_val = prod_val.__mul__(x)
      val = prod_val
    elif self.type == '/':
      val1 = self.evaluate_recurse(expr.children[0] , self.env, 'div0', reflip)
      val2 = self.evaluate_recurse(expr.children[1] , self.env, 'div1', reflip)
      val = val1.__div__(val2)
    else:
      raise Exception('Invalid expression type %s' % self.type)

    self.val = val
    self.active = True

    if self.assume:
      assert self.parent is None
      self.env.set(self.assume_name, val) # Environment in which this was evaluated

    return val

  def reflip(self, force_val = None):
    #if use_jit:
    #  jitdriver.jit_merge_point(node=self.val)
    self.evaluate(reflip = 0.5, xrp_force_val = force_val)
    assert self.random_xrp_apply
    self.propogate_up(True)
    return self.val

  def str_helper(self, n = 0, verbose = True):
    string = "\n" + (' ' * n) + "|- "
    if self.assume_name is not None:
      string += self.assume_name 
    elif verbose:
      string += str(self.expression)
    else:
      string += self.type 
    if not self.active:
      string += ", INACTIVE"
    else:
      string += ", VALUE = " + str(self.val)
      for key in self.children:
        string += self.children[key].str_helper(n + 2)
      for key in self.applychildren:
        string += self.applychildren[key].str_helper(n + 2)
    return string

  def __str__(self):
    if self.assume_name is None:
      return ("EvalNode of type %s, with expression %s and value %s" % (self.type, str(self.expression), str(self.val)))
    else:
      return ("EvalNode %s" % (self.assume_name))

class Traces(Engine):
  def __init__(self, env):
    self.assumes = []
    self.observes = {} # just a set

    self.db = RandomChoiceDict() 

    env.reset()
    self.env = env

    self.uneval_p = 0
    self.eval_p = 0
    self.p = 0
    return

  def assume(self, name, expr):
    evalnode = EvalNode(self, self.env, expr)

    self.assumes.append(evalnode)
    val = evalnode.evaluate()
    self.env.add_assume(name, evalnode)
    evalnode.add_assume(name, self.env)
    self.env.set(name, val)
    return val

  def sample(self, expr):
    evalnode = EvalNode(self, self.env, expr)
    val = evalnode.evaluate(False)
    evalnode.unevaluate()
    return val  

  def observe(self, expr, obs_val, id):
    evalnode = EvalNode(self, self.env, expr)

    assert id not in self.observes
    self.observes[id] = evalnode

    evalnode.observe(obs_val)
    evalnode.evaluate()

    return evalnode

  def forget(self, id):
    assert id in self.observes
    evalnode = self.observes[id]
    evalnode.unevaluate()
    del self.observes[id]
    return

  def rerun(self, reflip):
    for assume_node in self.assumes:
      assume_node.evaluate(reflip)
    for observe_node in self.observes.values():
      observe_node.evaluate(reflip)

  def reflip(self, reflip_node):
    debug = False

    if debug:
      old_self = self.__str__()

    assert reflip_node.random_xrp_apply
    assert reflip_node.val is not None
    
    self.eval_p = 0
    self.uneval_p = 0

    old_p = self.p
    old_val = reflip_node.val
    new_to_old_q = reflip_node.p
    old_to_new_q = - math.log(self.db.__len__())
    new_val = reflip_node.reflip()
    new_to_old_q -= math.log(self.db.__len__())
    old_to_new_q += reflip_node.p

    if debug:
      print "\n-----------------------------------------\n"
      print old_self
      print "\nCHANGING ", reflip_node, "\n  FROM  :  ", old_val, "\n  TO   :  ", new_val, "\n"
      if old_val == new_val:
        print "SAME VAL"
        print "new:\n", self
        return
  
    new_p = self.p
    eval_p = self.eval_p
    uneval_p = self.uneval_p
    if debug:
      print "new db", self
      print "\nq(old -> new) : ", math.exp(old_to_new_q)
      print "q(new -> old) : ", math.exp(new_to_old_q )
      print "p(old) : ", math.exp(old_p)
      print "p(new) : ", math.exp(new_p)
      print 'transition prob : ',  math.exp(new_p + new_to_old_q - old_p - old_to_new_q) , "\n"

    self.eval_p = 0
    self.uneval_p = 0
  
    p = rrandom.random.random()
    if new_p + new_to_old_q - old_p - old_to_new_q < math.log(p):
      new_val = reflip_node.reflip(old_val)

      if debug: 
        print 'restore'
        #print "original uneval", math.exp(uneval_p)
        #print "original eval", math.exp(eval_p)
        #print "new uneval", math.exp(self.uneval_p)
        #print "new eval", math.exp(self.eval_p)

      #assert self.p == old_p
      #assert self.uneval_p  + uneval_p == eval_p + self.eval_p

      #assert self.uneval_p == eval_p
      #assert self.eval_p == uneval_p
      # May not be true, because sometimes things get removed then incorporated
    if debug:
      print "new:\n", self

  # Add an XRP application node to the db
  def add_xrp(self, args, evalnodecheck = None):
    evalnodecheck.setargs(args)
    assert not self.db.__contains__(evalnodecheck)
    self.db.__setitem__(evalnodecheck, True)

  def remove_xrp(self, evalnode):
    assert self.db.__contains__(evalnode)
    self.db.__delitem__(evalnode)

  def infer(self):
    try:
      evalnode = self.db.randomKey()
    except:
      # No coin flips!
      return
    self.reflip(evalnode)

  def reset(self):
    self.__init__(self.env)
    
  def __str__(self):
    string = "EvalNodeTree:"
    for evalnode in self.assumes:
      string += evalnode.str_helper()
    return string
