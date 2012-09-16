import globals
from globals import Environment, RandomDB
from expressions import *

def reset():
  globals.env.assignments = {}
  globals.db.reset()
  globals.mem.reset()

def assume_helper(varname, expr, reflip):
  value = evaluate(expr, globals.env, reflip = reflip, stack = [varname])
  globals.env.set(varname, value)
  return value

def assume(varname, expr):
  expr = expression(expr)
  globals.mem.add('assume', (varname, expr))
  return assume_helper(varname, expr, True)

def observe_helper(expr, obs_val):
  # bit of a hack, here, to make it recognize same things as with noisy_expr
  val = evaluate(expr, globals.env, reflip = False, stack = ['obs', expr.hashval], xrp_force_val = obs_val)

def observe(expr, obs_val):
  expr = expression(expr)
  obs_val = value(obs_val)
  assert expr.type == 'apply' and expr.op.type == 'value' 
  assert expr.op.val.type == 'xrp'
  globals.mem.add('observe', (expr, obs_val))
  observe_helper(expr, obs_val)
  return expr.hashval 

def forget(hashval):
  globals.db.remove(['obs', hashval])
  globals.mem.forget(hashval)

# Replaces variables with the values from the environment 
def replace(expr, env, bound = set()):
  if expr.type == 'value':
    return expr
  elif expr.type == 'variable':
    if expr.name in bound:
      return expr
    val = env.lookup(expr.name)
    if val is None:
      return expr
      #warnings.warn('Unbound free variable %s' % expr.name)  ... not necessarily bad 
    else:
      return Expression(val)
  elif expr.type == 'if':
    cond = replace(expr.cond, env, bound)
    true = replace(expr.true, env, bound)
    false = replace(expr.false, env, bound)
    return Expression(('if', cond, true, false)) 
  elif expr.type == 'switch':
    index = replace(expr.index, env, bound)
    children = [replace(x, env, bound) for x in expr.children]
    return Expression(('switch', index, children)) 
  elif expr.type == 'let':
    expressions = [replace(x, env, bound) for x in expr.expressions]
    for var in expr.vars:
      bound.add(var)
    body = replace(expr.body, env, bound)
    return Expression(('let', expr.vars, expressions, body)) 
  elif expr.type == 'apply':
    # hmm .. replace non-bound things in op?  causes recursion to break...
    children = [replace(x, env, bound) for x in expr.children] 
    return Expression(('apply', expr.op, children)) 
  elif expr.type == 'function':
    # hmm .. replace variables?  maybe wipe those assignments out ...
    children = [replace(x, env, bound) for x in expr.children] 

    for var in expr.vars: # do we really want this?  probably.  (this is the only reason we use 'bound' at all
      bound.add(var)

    body = replace(expr.body, env, bound)
    return Expression(('function', expr.vars, body)) 
  elif expr.type in ['=', '<', '>', '>=', '<=', '&', '^', '|', 'add', 'subtract', 'multiply']:
    children = [replace(x, env, bound) for x in expr.children] 
    return Expression((expr.type, children)) 
  elif expr.type == '~':
    return Expression(('not', replace(expr.negation, env, bound))) 
  else:
    warnings.warn('Invalid expression type %s' % expr.type)
    return None

# Draws a sample value (without re-sampling other values) given its parents, and sets it
def evaluate(expr, env = None, reflip = False, stack = [], xrp_force_val = None):
  if env is None:
    env = globals.env

  expr = expression(expr)

  def evaluate_recurse(subexpr, env, reflip, stack, additions, xrp_force_val = None):
    if type(additions) != list:
      additions = [additions]
    n = len(additions)
    stack.extend(additions)
    val = evaluate(subexpr, env, reflip, stack)
    for i in xrange(n):
      stack.pop()
    return val

  def binary_op_evaluate(expr, env, reflip, stack, op): 
    val1 = evaluate_recurse(expr.children[0], env, reflip, stack, 0, xrp_force_val).val
    val2 = evaluate_recurse(expr.children[1], env, reflip, stack, 1, xrp_force_val).val
    return Value(op(val1 , val2))

  def list_op_evaluate(expr, env, reflip, stack, op):
    vals = [evaluate_recurse(expr.children[i], env, reflip, stack, i, xrp_force_val).val for i in xrange(len(expr.children))]
    return Value(reduce(op, vals))

  if expr.type == 'value':
    return expr.val
  elif expr.type == 'variable':
    var = expr.name
    val = env.lookup(var)
    if val is None:
      #warnings.warn('Variable %s undefined' % var)
      print 'Variable %s undefined' % var
      print env
      print stack
      assert False
    else:
      return val
  elif expr.type == 'if':
    cond = evaluate_recurse(expr.cond, env, reflip, stack , -1, xrp_force_val)
    assert type(cond.val) in [bool] 
    if cond.val: 
      globals.db.unevaluate(stack + [0])
      return evaluate_recurse(expr.true, env, reflip, stack , 1, xrp_force_val)
    else:
      globals.db.unevaluate(stack + [1])
      return evaluate_recurse(expr.false, env, reflip, stack , 0, xrp_force_val)
  elif expr.type == 'switch':
    index = evaluate_recurse(expr.index, env, reflip, stack , -1, xrp_force_val)
    assert type(index.val) in [int] 
    assert 0 <= index.val < expr.n
    # unevaluate?
    return evaluate_recurse(expr.children[index.val], env, reflip, stack, index.val, xrp_force_val)
  elif expr.type == 'let':
    # TODO:think more about the behavior with environments here...
    n = len(expr.vars)
    assert len(expr.expressions) == n
    values = []
    new_env = env
    for i in range(n): # Bind variables
      new_env = new_env.spawn_child()
      val = evaluate_recurse(expr.expressions[i], new_env, reflip, stack, i, xrp_force_val)
      values.append(val)
      new_env.set(expr.vars[i], values[i])
      if val.type == 'procedure':
        val.env = new_env
    new_body = replace(expr.body, new_env)
    return evaluate_recurse(new_body, new_env, reflip, stack, -1, xrp_force_val)
  elif expr.type == 'apply':
    n = len(expr.children)
    args = [evaluate_recurse(expr.children[i], env, reflip, stack, i, xrp_force_val) for i in range(n)]
    op = evaluate_recurse(expr.op, env, reflip, stack , -2, xrp_force_val)
    if op.type == 'procedure':
      globals.db.unevaluate(['procedure', hash(op)], args)
      if n != len(op.vars):
        print 'Should have %d arguments' % n
        print op.vars
        print expr.children
        assert False
      new_env = op.env.spawn_child()
      for i in range(n):
        new_env.set(op.vars[i], args[i]) 
      return evaluate(op.body, new_env, reflip, ['procedure', hash(op), tuple(args)], xrp_force_val)
    elif op.type == 'xrp':
      globals.db.unevaluate(stack + [-1], args)

      if xrp_force_val != None: 
        if globals.db.has(stack):
          globals.db.remove(stack)
        globals.db.insert(stack, op.val, xrp_force_val, args, True) 
        return xrp_force_val

      stack.extend([-1, tuple(args)])
      if not globals.db.has(stack):
        val = value(op.val.apply(args))
        globals.db.insert(stack, op.val, val, args)
      else:
        if reflip:
          globals.db.remove(stack)
          val = value(op.val.apply(args))
          globals.db.insert(stack, op.val, val, args)
        else:
          (xrp, val, dbargs, is_obs_noise) = globals.db.get(stack) 
          #assert xrp == op.val 
          #assert dbargs == args 
          assert not is_obs_noise
      stack.pop()
      stack.pop()
      return val
    else:
      warnings.warn('Must apply either a procedure or xrp')
  elif expr.type == 'function':
    n = len(expr.vars)
    new_env = env.spawn_child()
    for i in range(n): # Bind variables
      new_env.set(expr.vars[i], expr.vars[i])
    procedure_body = replace(expr.body, new_env)
    return Value((expr.vars, procedure_body), env)
  elif expr.type == '=':
    return binary_op_evaluate(expr, env, reflip, stack, lambda x, y : x == y)
  elif expr.type == '<':
    return binary_op_evaluate(expr, env, reflip, stack, lambda x, y : x < y)
  elif expr.type == '>':
    return binary_op_evaluate(expr, env, reflip, stack, lambda x, y : x > y)
  elif expr.type == '<=':
    return binary_op_evaluate(expr, env, reflip, stack, lambda x, y : x <= y)
  elif expr.type == '>=':
    return binary_op_evaluate(expr, env, reflip, stack, lambda x, y : x >= y)
  elif expr.type == '&':
    return list_op_evaluate(expr, env, reflip, stack, lambda x, y : x & y)
  elif expr.type == '^':
    return list_op_evaluate(expr, env, reflip, stack, lambda x, y : x ^ y)
  elif expr.type == '|':
    return list_op_evaluate(expr, env, reflip, stack, lambda x, y : x | y)
  elif expr.type == '~':
    negval = evaluate_recurse(expr.negation, env, reflip, stack, 0).val
    return Value(not negval)
  elif expr.type == 'add':
    return list_op_evaluate(expr, env, reflip, stack, lambda x, y : x + y)
  elif expr.type == 'subtract':
    val1 = evaluate_recurse(expr.children[0], env, reflip, stack , 0).val
    val2 = evaluate_recurse(expr.children[1], env, reflip, stack , 1).val
    return Value(val1 - val2)
  elif expr.type == 'multiply':
    return list_op_evaluate(expr, env, reflip, stack, lambda x, y : x * y)
  else:
    warnings.warn('Invalid expression type %s' % expr.type)
    return None

def sample(expr, env = None, varname = None, reflip = False):
  expr = expression(expr)
  if env is None:
    env = globals.env
  if varname is None:
    return evaluate(expr, env, reflip, ['expr', expr.hashval])
  else:
    return evaluate(expr, env, reflip, [varname])

def resample(expr, env = None, varname = None):
  return sample(expr, env, varname, True)

# OUTDATED
def reject_infer():
  flag = False
  while not flag:
    rerun(True)

    # Reject if observations untrue
    flag = True
    for obs_hash in globals.mem.observes:
      (obs_expr, obs_val) = globals.mem.observes[obs_hash] 
      val = resample(obs_expr)
      if val.val != obs_val:
        flag = False
        break

# Rejection based inference
def reject_infer_many(name, niter = 1000):
  if name in globals.mem.vars:
    expr = globals.mem.vars[name]
  else:
    warnings.warn('%s is not defined' % str(name))

  dict = {}
  for n in xrange(niter):
    # Re-draw from prior
    reject_infer()
    ans = evaluate(expr, globals.env, False, [name]) 

    if ans.val in dict:
      dict[ans.val] += 1
    else:
      dict[ans.val] = 1

  z = sum([dict[val] for val in dict])
  for val in dict:
    dict[val] = dict[val] / (z + 0.0) 
  return dict 

def rerun(reflip):
# Class representing environments
  for (varname, expr) in globals.mem.assumes:
    assume_helper(varname, expr, reflip)
  for hashval in globals.mem.observes:
    (expr, obs_val) = globals.mem.observes[hashval] 
    observe_helper(expr, obs_val)

def infer(): # RERUN AT END
  
  # reflip some coin
  stack = globals.db.random_stack() 
  (xrp, val, args, is_obs_noise) = globals.db.get(stack)

  debug = True 
  #debug = False 

  old_p = globals.db.p
  old_to_new_q = - math.log(globals.db.count) 
  if debug:
    print  "old_db", globals.db

  globals.db.save()

  globals.db.remove(stack)
  new_val = xrp.apply(args)
  globals.db.insert(stack, xrp, new_val, args)

  if debug:
    print "\nCHANGING ", stack, "\n  TO   :  ", new_val, "\n"

  if val == new_val:
    return

  rerun(False)
  new_p = globals.db.p
  new_to_old_q = globals.db.uneval_p - math.log(globals.db.count) 
  old_to_new_q += globals.db.eval_p 
  if debug:
    print "new db", globals.db
    print "\nq(old -> new) : ", old_to_new_q
    print "q(new -> old) : ", new_to_old_q 
    print "p(old) : ", old_p
    print "p(new) : ", new_p
    print 'log transition prob : ',  new_p + new_to_old_q - old_p - old_to_new_q , "\n"

  if old_p * old_to_new_q > 0:
    p = random.random()
    if new_p + new_to_old_q - old_p - old_to_new_q < math.log(p):
      globals.db.restore()
      if debug: 
        print 'restore'

  if debug: 
    print "new db", globals.db
    print "\n-----------------------------------------\n"

def follow_prior(name, niter = 1000, burnin = 100):

  #return reject_infer_many(name, niter)

  if name in globals.mem.vars:
    expr = globals.mem.vars[name]
  else:
    warnings.warn('%s is not defined' % str(name))

  dict = {}
  for n in xrange(niter):
    if n % 100 == 0: print n

    # re-draw from prior
    rerun(True)
    for t in xrange(burnin):
      infer()

    rerun(False) 
    val = evaluate(name, globals.env, reflip = False, stack = [name])
    if val in dict:
      dict[val] += 1
    else:
      dict[val] = 1

  return dict 
