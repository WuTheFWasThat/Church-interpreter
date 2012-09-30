from expressions import *
from random_choice_dict import *
import sys

# Class representing environments
class Environment:
  def __init__(self, parent = None):
    self.parent = parent # The parent environment
    self.assignments = {} # Dictionary from names to values
    self.children = set() 
    if parent is not None:
      self.parent.children.add(self)

    self.assumes = {}
    self.lookups = {}
    return

  def set(self, name, expression):
    self.assignments[name] = expression

  def lookup(self, name):
    if name in self.assignments:
      return (self.assignments[name], self)
    else:
      if self.parent is None:
        warnings.warn('Variable %s undefined in env:\n%s' % (var, str(env)))
        assert False
      else:
        return self.parent.lookup(name)

  def add_assume(self, name, evalnode):
    self.assumes[name] = evalnode
    evalnode.add_assume(name, self)

  def add_lookup(self, name, evalnode):
    if name in self.lookups:
      self.lookups[name].add(evalnode)
    else:
      self.lookups[name] = set([evalnode])

  def rem_lookup(self, name, evalnode):
    assert name in self.lookups
    self.lookups[name].remove(evalnode)

  def get_lookups(self, name, evalnode):
    assert name in self.assumes
    assert self.assumes[name] is evalnode
    return self.lookups[name]

  def spawn_child(self): 
    return Environment(self)

  def __setitem__(self, name, expression):
    self.set(name, expression) 

  def __getitem__(self, name):
    return self.lookup(name) 

  def __str__(self):
    return self.assignments.__str__()

class EvalNode:
  def __init__(self, traces, stack, env, expression):
    self.parent = None 
    self.children = {} 
    self.applychildren = {} 

    self.active = False # Whether this node is currently activated

    self.env = env # Environment in which this was evaluated
    self.lookup = None 
    self.assume = False
    self.assume_name = None

    self.expr = expression 

    self.observed = False
    self.observe_val = None 

    self.random_xrp_apply = False

    self.stack = stack
    self.expression = expression
    self.type = expression.type

    self.val = None

    self.args = None

    self.traces = traces
    return

  def get_child(self, addition, env, subexpr):
    if type(addition) == tuple:
      if addition not in self.applychildren:
        self.spawnchild(addition, env, subexpr, True)
      return self.applychildren[addition]
    else:
      if addition not in self.children:
        self.spawnchild(addition, env, subexpr, False)
      return self.children[addition]
  
  def spawnchild(self, addition, env, subexpr, is_apply):
    newstack = self.stack + [addition]
    child = EvalNode(self.traces, newstack, env, subexpr)
    child.parent = self
    if is_apply:
      self.applychildren[addition] = child
    else:
      self.children[addition] = child
    self.traces.evalnodes[tuple(newstack)] = child 

  def add_assume(self, name, env):
    assert env == self.env
    self.assume_name = name
    self.assume = True

  def observe(self, obs_val):
    self.observed = True
    self.observe_val = obs_val

  def setlookup(self, env):
    assert self.expr.type == 'variable'
    self.lookup = env 
    env.add_lookup(self.expr.name, self)

  def remlookup(self, name, env):
    self.lookup = None
    env.rem_lookup(name, self)

  def setvalue(self, value):
    self.active = True
    self.val = value

  def addchild(self, child, addition):
    if type(addition) == tuple:
      self.applychildren[addition] = child
    else:
      self.children[addition] = child

  def setargs(self, args):
    assert self.type == 'apply'
    self.args = args

  def propogate_up(self):
    assert self.active
    if self.observed:
      val = self.evaluate(reflip = False, xrp_force_val = self.observe_val)
      assert val == self.val
    elif self.random_xrp_apply:
      val = self.evaluate(reflip = False, xrp_force_val = self.val)
      assert val == self.val
    else:
      val = self.evaluate(reflip = False, xrp_force_val = None)
      if self.assume:
        assert self.parent is None
        self.parent.propogate_up()
        for evalnode in self.env.get_lookups(self.assume_name, self.evalnode):
          evalnode.propogate_up()

    self.val = val
    return self.val

  def unevaluate(self):
    if not self.active:
      return
    if self.type == 'variable':
      self.remlookup(self.name, lookup_env)
    elif self.type == 'apply':
      args = [self.get_child(i, self.env, self.expr.children[i]).unevaluate() for i in range(len(self.expr.children))]
      op = self.get_child(-2, self.env, self.expr.op).unevaluate()
      if op.type == 'procedure':
        new_env = op.env.spawn_child()
        for i in range(n):
          new_env.set(op.vars[i], args[i])
        val = self.get_child((-1, tuple(hash(x) for x in args)), self.env, op.body).unevaluate()
      elif op.type == 'xrp':
        xrp = op.val
        assert args == self.args
        xrp.remove(self.val, self.args)
        prob = xrp.prob(self.val, self.args)
        self.traces.uneval_p += prob
        self.traces.p -= prob

        if not xrp.deterministic:
          self.remove_xrp(self)
    else:
      for x in self.children:
        self.children[x].unevaluate()

    self.active = False
    return self.val

  def remove_xrp(self, stack):
    self.traces.remove_xrp(stack)

  def evaluate(self, reflip = False, xrp_force_val = None):
    if reflip == False and self.active:
      assert self.val is not None
      return self.val

    def evaluate_recurse(subexpr, env, stack, addition):
      val = self.get_child(addition, env, subexpr).evaluate(reflip == True)
      return val
  
    def binary_op_evaluate(op):
      val1 = evaluate_recurse(self.expr.children[0], self.env, self.stack, 0).val
      val2 = evaluate_recurse(self.expr.children[1], self.env, self.stack, 1).val
      return Value(op(val1 , val2))

    def list_op_evaluate(op):
      vals = [evaluate_recurse(self.expr.children[i], self.env, self.stack, i).val for i in xrange(len(self.expr.children))]
      return Value(reduce(op, vals))
  
    if xrp_force_val is not None:
      assert self.type == 'apply'

    if self.type == 'value':
      val = self.expr.val
    elif self.type == 'variable':
      # TODO : is this right?
      (val, lookup_env) = self.env.lookup(self.expr.name)
      self.setlookup(lookup_env)
    elif self.type == 'if':
      cond = evaluate_recurse(self.expr.cond, self.env, self.stack, -1)
      assert type(cond.val) in [bool]
      if cond.val:
        self.get_child(0, self.env, self.expr.false).unevaluate()
        val = evaluate_recurse(self.expr.true, self.env, self.stack, 1)
      else:
        self.get_child(1, self.env, self.expr.true).unevaluate()
        val = evaluate_recurse(self.expr.false, self.env, self.stack, 0)
    elif self.type == 'switch':
      index = evaluate_recurse(self.expr.index , self.env, self.stack, -1)
      assert type(index.val) in [int]
      assert 0 <= index.val < self.expr.n
      for i in range(self.expr.n):
        if i != index.val:
          self.get_child(i, self.env, self.expr.children[i]).unevaluate()
      val = evaluate_recurse(self.children[index.val] , self.env, self.stack, index.val)
    elif self.type == 'let':
      # TODO: think more about the behavior with environments here...
      # TODO: fix.  similar situation to lambda
      
      #n = len(expr.vars)
      #assert len(expr.expressions) == n
      #values = []
      #new_env = env
      #for i in range(n): # Bind variables
      #  new_env = new_env.spawn_child()
      #  val = evaluate_recurse(self.expr.expressions[i] , self.env, self.stack, i)
      #  values.append(val)
      #  new_env.set(expr.vars[i], values[i])
      #  if val.type == 'procedure':
      #    val.env = new_env
      #new_body = replace(expr.body, new_env)
      #val = evaluate_recurse(self.expr.body , self.env, self.stack, -1)

      val = self.val
    elif self.type == 'apply':
      args = [evaluate_recurse(self.expr.children[i], self.env, self.stack, i) for i in range(len(self.expr.children))]
      op = evaluate_recurse(self.expr.op, self.env, self.stack, -2)
      if op.type == 'procedure':
        for x in self.applychildren:
          if x != tuple(hash(x) for x in args):
            self.applychildren[x].unevaluate()

        if n != len(op.vars):
          warnings.warn('Procedure should have %d arguments.  \nVars were \n%s\n, but children were \n%s.' % (n, op.vars, self.chidlren))
          assert False
        new_env = op.env.spawn_child()
        for i in range(n):
          new_env.set(op.vars[i], args[i])
        val = evaluate_recurse(op.body, self.env, self.stack, (-1, tuple(hash(x) for x in args)))
      elif op.type == 'xrp':
        xrp = op.val
        if not xrp.deterministic:
          self.random_xrp_apply = True
          self.traces.add_xrp(self.stack, args)

        if xrp_force_val != None:
          assert reflip != True
          assert not self.active
          val = xrp_force_val
        elif self.active:
          if not reflip:
            val = self.val
          else:
            xrp.remove(self.val, self.args)
            prob = xrp.prob(self.val, self.args)
            self.traces.uneval_p += prob
            self.traces.p -= prob

            self.args = args
            val = value(xrp.apply(args))
        else:
            self.args = args
            val = value(xrp.apply(args))
        prob = xrp.prob(val, args)
        self.traces.eval_p += prob
        self.traces.p += prob
        xrp.incorporate(val, args)
        # TODO
        # assert not is_obs_noise
      else:
        warnings.warn('Must apply either a procedure or xrp')
    elif self.type == 'function':
      val = self.val
      # TODO: fix
      #n = len(expr.vars)
      #new_env = env.spawn_child()
      #for i in range(n): # Bind variables
      #  new_env.set(expr.vars[i], expr.vars[i])
      #procedure_body = replace(expr.body, new_env)
      #val = Value((expr.vars, procedure_body, stack), env)
      #TODO: SET SOME RELATIONSHIP HERE?  If body contains reference to changed var...
    elif self.type == '=':
      val = binary_op_evaluate(lambda x, y : x == y)
    elif self.type == '<':
      val = binary_op_evaluate(lambda x, y : x < y)
    elif self.type == '>':
      val = binary_op_evaluate(lambda x, y : x > y)
    elif self.type == '<=':
      val = binary_op_evaluate(lambda x, y : x <= y)
    elif self.type == '>=':
      val = binary_op_evaluate(lambda x, y : x >= y)
    elif self.type == '&':
      val = list_op_evaluate(lambda x, y : x & y)
    elif self.type == '^':
      val = list_op_evaluate(lambda x, y : x ^ y)
    elif self.type == '|':
      val = list_op_evaluate(lambda x, y : x | y)
    elif self.type == '~':
      negval = evaluate_recurse(self.expr.negation , self.env, self.stack, 0).val
      val = Value(not negval)
    elif self.type == 'add':
      val = list_op_evaluate(lambda x, y : x + y)
    elif self.type == 'subtract':
      val1 = evaluate_recurse(self.expr.children[0] , self.env, self.stack, 0).val
      val2 = evaluate_recurse(self.expr.children[1] , self.env, self.stack, 1).val
      val = Value(val1 - val2)
    elif self.type == 'multiply':
      val = list_op_evaluate(lambda x, y : x * y)
    else:
      warnings.warn('Invalid expression type %s' % self.type)
      assert False

    self.val = val
    self.active = True

    return val

  def reflip(self, force_val = None):
    self.evaluate(reflip = 0.5, xrp_force_val = force_val)
    self.propogate_up()
    return self.val

  def str_helper(self, n = 0):
    string = "\n" + (' ' * n) + "|- "
    string += self.type + " at " + str(self.stack)
    string += ", VALUE = " + str(self.val)
    for key in self.children:
      string += self.children[key].str_helper(n + 2)
    for key in self.applychildren:
      string += self.applychildren[key].str_helper(n + 2)
    return string

  def __str__(self):
    return ("EvalNode of type %s at %s" % (self.type, str(self.stack)))

class Traces:
  def __init__(self, env):
    self.evalnodes = {}

    self.roots = set() # set of evalnodes with no parents
    # TODO:  remove?  or also have leaves?

    self.db = RandomChoiceDict() 

    self.global_env = env

    self.uneval_p = 0
    self.eval_p = 0
    self.p = 0
    return

  def assume(self, name, expr):
    evalnode = EvalNode(self, [name], env, expr)
    stack = tuple([name])
    self.evalnodes[stack] = evalnode 
    self.roots.add(evalnode)
    val = evalnode.evaluate()
    self.global_env.add_assume(name, evalnode)
    self.global_env.set(name, val)
    return val

  def setvalue(self, stack, value):
    stack = tuple(stack)
    self.get(stack).setvalue(value)

  def has(self, stack):
    return tuple(stack) in self.evalnodes

  def get(self, stack):
    stack = tuple(stack)
    assert self.has(stack)
    return self.evalnodes[stack]

  def reflip(self, reflip_node):
    debug = True

    if debug:
      print "\n-----------------------------------------\n"
      print self

    assert reflip_node.type == 'apply'
    assert reflip_node.val is not None
    
    self.eval_p = 0
    self.uneval_p = 0

    old_p = self.p
    old_val = reflip_node.val
    old_count = len(self.db)
    new_val = reflip_node.reflip()
    new_count = len(self.db)

    assert -2 in reflip_node.children
    assert reflip_node.children[-2].val.type == 'xrp'
    xrp = reflip_node.children[-2].val.val

    #print old_val, old_count, new_val, new_count

    if debug:
      print "\nCHANGING ", reflip_node, "\n  TO   :  ", new_val, "\n"
      if old_val == new_val:
        print "SAME VAL"
        return
  
    new_p = self.p
    uneval_p = self.uneval_p
    eval_p = self.eval_p
    new_to_old_q = uneval_p - math.log(new_count) 
    old_to_new_q = eval_p - math.log(old_count)
    if debug:
      print "new db", len(self.db)
      print "\nq(old -> new) : ", old_to_new_q
      print "q(new -> old) : ", new_to_old_q 
      print "p(old) : ", old_p
      print "p(new) : ", new_p
      print 'log transition prob : ',  new_p + new_to_old_q - old_p - old_to_new_q , "\n"
  
    if old_p * old_to_new_q > 0:
      p = random.random()
      if new_p + new_to_old_q - old_p - old_to_new_q < math.log(p):
        if debug: 
          print 'restore'
        new_val = reflip_node.reflip(old_val)
        assert self.p == old_p
        assert self.uneval_p == eval_p
        assert self.eval_p == uneval_p
  
    if debug: 
      print "new ", self

    # ENVELOPE CALCULATION?

  def evaluate(self, expression):
    evalnode = EvalNode(self, [], self.global_env, expression)
    return evalnode.evaluate()

  #def evaluate(self, stack, reflip = False, xrp_force_val = None):
  #  return self.get(stack).evaluate(reflip, xrp_force_val)

  # Add an XRP application node to the db
  def add_xrp(self, stack, args):
    #print stack
    stack = tuple(stack)
    assert stack in self.evalnodes
    evalnode = self.evalnodes[stack]
    evalnode.setargs(args)
    self.db[evalnode] = True

  def remove_xrp(self, evalnode):
    assert evalnode in self.db
    del self.db[evalnode] 

  def add_observe(self, stack, obs_val):
    self.get(stack).observe(obs_val)

  def random_stack(self):
    evalnode = self.db.randomKey()
    return evalnode

  def reset(self):
    self.__init__(self.global_env)
    
  def __setitem__(self, stack, tup):
    self.set(stack, tup) 

  def __getitem__(self, stack):
    return self.get(stack)

  def __str__(self):
    string = "EvalNodeTree:"
    for evalnode in self.roots:
      string += evalnode.str_helper()
    return string


# Class representing random db
class RandomDB:
  def __init__(self):
    #self.db = {} 
    self.db = RandomChoiceDict() 
    self.db_noise = {}
    # TODO: remove count
    self.count = 0
    assert self.count == len(self.db)
    self.memory = []
    # ALWAYS WORKING WITH LOG PROBABILITIES
    self.uneval_p = 0
    self.eval_p = 0
    self.p = 0 
    return

  def insert(self, stack, xrp, value, args, is_obs_noise = False, memorize = True):
    stack = tuple(stack)
    assert value.__class__.__name__ == 'Value'
    if self.has(stack):
      self.remove(stack)
    prob = xrp.prob(value, args)
    self.p += prob
    xrp.incorporate(value, args)
    if is_obs_noise:
      self.db_noise[stack] = (xrp, value, args, True)
    else:
      self.db[stack] = (xrp, value, args, False)
    if not is_obs_noise:
      self.count += 1
      self.eval_p += prob # hmmm.. 
      assert self.count == len(self.db)
    if memorize:
      self.memory.append(('insert', stack, xrp, value, args, is_obs_noise))

  def remove(self, stack, memorize = True):
    stack = tuple(stack)
    assert self.has(stack)
    (xrp, value, args, is_obs_noise) = self.get(stack)
    xrp.remove(value, args)
    prob = xrp.prob(value, args)
    self.p -= prob
    if is_obs_noise:
      del self.db_noise[stack]
    else:
      del self.db[stack]
      self.count -= 1
      assert self.count >= 0
      self.uneval_p += prob # previously unindented...
    assert self.count == len(self.db)
    if memorize:
      self.memory.append(('remove', stack, xrp, value, args, is_obs_noise))

  def has(self, stack):
    stack = tuple(stack)
    return ((stack in self.db) or (stack in self.db_noise)) 

  def get(self, stack):
    stack = tuple(stack)
    if stack in self.db:
      return self.db[stack]
    elif stack in self.db_noise:
      return self.db_noise[stack]
    else:
      warnings.warn('Failed to get stack %s' % str(stack))
      return None

  def random_stack(self):
    key = self.db.randomKey()
    return key

  #def prob(self):
  #  ans = 0
  #  for key in self.db:
  #    (xrp, value, prob, args, is_obs_noise) = self.db[key]
  #    ans += prob
  #  for key in self.db_noise:
  #    (xrp, value, prob, args, is_obs_noise) = self.db_noise[key]
  #    ans += prob
  #  return ans 

  def unevaluate(self, uneval_stack, args = None):
    if args is not None:
      args = tuple(args)

    to_delete = []

    def unevaluate_helper(tuple_stack):
      stack = list(tuple_stack) 
      if len(stack) >= len(uneval_stack) and stack[:len(uneval_stack)] == uneval_stack:
        if args is None:
          to_delete.append(tuple_stack)
        else:
          assert len(stack) > len(uneval_stack)
          if stack[len(uneval_stack)] != args:
            to_delete.append(tuple_stack)

    for tuple_stack in self.db:
      unevaluate_helper(tuple_stack)
    for tuple_stack in self.db_noise:
      unevaluate_helper(tuple_stack)

    for tuple_stack in to_delete:
      self.remove(tuple_stack)

  def save(self):
    self.memory = []
    self.uneval_p = 0
    self.eval_p = 0

  def restore(self):
    self.memory.reverse()
    for (type, stack, xrp, value, args, is_obs_noise) in self.memory:
      if type == 'insert':
        self.remove(stack, False)
      else:
        assert type == 'remove'
        self.insert(stack, xrp, value, args, is_obs_noise, False)

  def reset(self):
    #self.db = {} 
    self.db = RandomChoiceDict() 
    self.db_noise = {}
    self.count = 0
    assert self.count == len(self.db)
    self.save()
    self.p = 0

  def __str__(self):
    string = 'DB with state:'
    string += '\n  Regular Flips:'
    for s in self.db:
      string += '\n    %s <- %s' % (self.db[s][1].val, s) 
    string += '\n  Observe Flips:'
    for s in self.db_noise:
      string += '\n    %s <- %s' % (self.db_noise[s][1].val, s) 
    return string

  def __contains__(self, stack):
    return self.has(self, stack)

  def __getitem__(self, stack):
    return self.get(self, stack)

class Directives_Memory:
  def __init__(self):
    self.assumes = []
    self.observes = {}
    self.vars = {}

  def reset(self):
    self.__init__()

  def add(self, type, tup): 
    if type == 'assume':
      (varname, expr) = tup
      self.assumes.append(tup)
      self.vars[varname] = expr
    else:
      assert type == 'observe'
      (expr, obs_val) = tup
      if expr.hashval in self.observes:
        warnings.warn('Already observed %s' % str(expr))
      self.observes[expr.hashval] = tup 

  def forget(self, hashval):
    assert hashval in self.observes
    del self.observes[hashval]

# The global environment. Has assignments of names to expressions, and parent pointer 
env = Environment()

# The traces datastructure. 
# DAG of two interlinked trees: 
#   1. eval (with subcases: IF, symbollookup, combination, lambda) + apply
#   2. environments
# crosslinked by symbol lookup nodes and by the env argument to eval
traces = Traces(env)

# Table storing a list of (xrp, value, probability) tuples
db = RandomDB()

# Global memory.  List of (directive type, args)
mem = Directives_Memory() 

sys.setrecursionlimit(10000)
