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
    self.lookups = {}
    return

  def set(self, name, expression):
    self.assignments[name] = expression

  def lookup(self, name):
    if name in self.assignments:
      return (self.assignments[name], self)
    else:
      if self.parent is None:
        warnings.warn('At stack %s:\nVariable %s undefined in env:\n%s' % (str(stack), var, str(env)))
        assert False
      else:
        return self.parent.lookup(name)

  def add_lookup(self, name, evalnode):
    if name in self.lookups:
      self.lookups[name].add(evalnode)
    else:
      self.lookups[name] = set([evalnode])

  def spawn_child(self): 
    return Environment(self)

  def __setitem__(self, name, expression):
    self.set(name, expression) 

  def __getitem__(self, name):
    return self.lookup(name) 

  def __str__(self):
    return self.assignments.__str__()

class EvalNodeInstance:
  def __init__(self, stack, env, type, evalnodeset):
    self.parent = None 
    self.children = {} 

    self.env = env # Environment in which this was evaluated
    self.lookup = None 

    self.stack = stack
    self.type = type

    self.val = None
    self.evalnodeset = evalnodeset
    return

  def setparent(self, parent, addition):
    self.parent = parent
    self.parent.addchild(self, addition)

  def setlookup(self, name, env):
    self.lookup = env 
    env.add_lookup(name, self)

  def setvalue(self, value):
    self.val = value

  def addchild(self, child, addition):
    self.children[addition] = child

  def str_helper(self, prefix = ""):
    string = "\n"
    string += " " + prefix + str(self)
    for key in self.children:
      string += self.children[key].str_helper(prefix + "-")
    return string

  def __str__(self):
    return ("EvalNodeInstance of type %s at %s" % (self.type, str(self.stack)))

class EvalNode:
  def __init__(self, stack):
    self.evalnodes = set() 
    self.active_node = None
    self.proposed_node = None
    self.stack = stack
    
  def addnode(self, env, type):
    evalnode = EvalNodeInstance(self.stack, env, type, self)
    self.evalnodes.add(evalnode)
    # unactivate old node?
    self.active_node = evalnode

  def setparent(self, parent, addition):
    return self.active_node.setparent(parent, addition)

  def setlookup(self, name, env):
    return self.active_node.setlookup(name, env)

  def setvalue(self, value):
    return self.active_node.setvalue(value)

  def addchild(self, child, addition):
    return self.active_node.addchild(child, addition)

  def str_helper(self, prefix = ""):
    return self.active_node.str_helper(prefix)

class Traces:
  def __init__(self):
    self.evalnodes = {}
    self.roots = set() # set of evalnodes with no parents
    self.db = RandomChoiceDict() 
    # also have leaves?
    return

  def set(self, stack, tup):
    stack = tuple(stack)
    evalnodeset = EvalNode(stack)
    evalnodeset.addnode(tup[0], tup[1])
    self.evalnodes[stack] = evalnodeset 
    self.roots.add(stack)

  def setparent(self, parentstack, addition):
    stack = tuple(parentstack + [addition])
    parentstack = tuple(parentstack)
    if stack in self.roots:
      self.roots.remove(stack)
    self.get(stack).setparent(self.get(parentstack), addition)

  def setlookup(self, stack, name, lookup_env):
    stack = tuple(stack)
    self.get(stack).setlookup(name, lookup_env)
  
  def setvalue(self, stack, value):
    stack = tuple(stack)
    self.get(stack).setvalue(value)

  def has(self, stack):
    return tuple(stack) in self.evalnodes

  def get(self, stack):
    assert self.has(stack)
    return self.evalnodes[stack]

  def reflip(self, stack):
    reflip_node = self.get(stack).active_node
    assert reflip_node.type == 'apply'
    print self.db
    #print self
    assert -2 in reflip_node.children
    assert reflip_node.children[-2].val.type == 'xrp'
    xrp = reflip_node.children[-2].val.val
    # TODO
    # ENVELOPE CALCULATION?
    # UNFINIHSED

  def propogate_up(self, stack):
    # IF
    # nondeterministic XRP - stop
    # env lookup
    pass

  # Add an XRP application node to the db
  def add_xrp(self, stack):
    stack = tuple(stack)
    self.db[stack] = stack 

  def unevaluate(self, uneval_stack, exception = None):
    if args is not None:
      args = tuple(args)
    uneval_stack = tuple(uneval_stack)
    self.get(uneval_stack)
    
    # TODO
    # remove from db
    # track probability
    # allow undoing

  def random_stack(self):
    stack = self.db.randomKey()
    return stack

  def reset(self):
    self.__init__()
    
  def __setitem__(self, stack, tup):
    self.set(stack, tup) 

  def __getitem__(self, stack):
    return self.get(stack)

  def __str__(self):
    string = "EvalNodeTree:"
    for rootstack in self.roots:
      string += self.get(rootstack).str_helper()
    return string


# Class representing random db
class RandomDB:
  def __init__(self):
    #self.db = {} 
    self.db = RandomChoiceDict() 
    self.db_noise = {}
    self.count = 0
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
    if memorize:
      self.memory.append(('insert', stack, xrp, value, args, is_obs_noise))

  def remove(self, stack, memorize = True):
    stack = tuple(stack)
    assert self.has(stack)
    (xrp, value, args, is_obs_noise) = self.get(stack)
    xrp.remove(value, args)
    prob = xrp.prob(value, args)
    self.p -= prob
    if not is_obs_noise:
      self.count -= 1
      assert self.count >= 0
      self.uneval_p += prob # previously unindented...
    if is_obs_noise:
      del self.db_noise[stack]
    else:
      del self.db[stack]
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
traces = Traces()

# Table storing a list of (xrp, value, probability) tuples
db = RandomDB()

# Global memory.  List of (directive type, args)
mem = Directives_Memory() 

sys.setrecursionlimit(10000)
