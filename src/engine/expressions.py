from values import *
from xrp import *

#Class representing expressions 
class Expression:
  # Replaces variables with the values from the environment 
  def __init__(self):
    self.hashval = rrandom.random.randbelow()

  def initialize(self):
    # dummy values to prevent RPython typer from complaining 
    self.cond = Expression()
    self.true = Expression()
    self.false = Expression()

    self.op = Expression()
    self.vars = ['']

    self.body = Expression()

    self.children = [Expression()]
    self.expressions = [Expression()]

    # initialize hash value
    self.hashval = rrandom.random.randbelow()
    pass

  def replace(self, env, bound = {}):
    pass
  def __eq__(self, other):
    return OpExpression('=', [self, other])
  def __lt__(self, other):
    return OpExpression('<', [self, other])
  def __le__(self, other):
    return OpExpression('<=', [self, other])
  def __gt__(self, other):
    return OpExpression('>', [self, other])
  def __ge__(self, other):
    return OpExpression('>=', [self, other])
  def __add__(self, other):
    return OpExpression('+', [self, other])
  def __sub__(self, other):
    return OpExpression('-', [self, other])
  def __mul__(self, other):
    return OpExpression('*', [self, other])
  def __div__(self, other):
    return OpExpression('/', [self, other])
  def __and__(self, other):
    return OpExpression('&', [self, other])
  def __or__(self, other):
    return OpExpression('|', [self, other])
  def __xor__(self, other):
    return OpExpression('^', [self, other])
  def __invert__(self):
    return OpExpression('~', [self])
  def __str__(self):
    return "Expression"
  def __repr__(self):
    return self.__str__()
  def __hash__(self):
    return self.hashval
                                            

class ConstExpression(Expression):
  def __init__(self, value):
    self.initialize()
    self.val = value
    self.type = 'value'

  def replace(self, env, bound = {}):
    return self

  def __str__(self):
    return str(self.val)

class VarExpression(Expression):
  def __init__(self, name):
    self.initialize()
    self.type = 'variable'
    self.name = name

  def replace(self, env, bound = {}):
    if self.name in bound:
      return self
    (val, lookup_env) = env.lookup(self.name)
    if val is None:
      return self
    else:
      return ConstExpression(val)
  
  def __str__(self):
    return self.name

class ApplyExpression(Expression):
  def __init__(self, op, children):
    self.initialize()
    self.type = 'apply'
    self.op = op
    self.children = children
    if self.op.type == 'function' and len(self.op.vars) < len(self.children):
      raise Exception('Applying function to too many arguments!')

  def replace(self, env, bound = {}):
    # TODO hmm .. replace non-bound things in op?  causes recursion to break...
    children = [x.replace(env, bound) for x in self.children] 
    return ApplyExpression(self.op, children)
  
  def __str__(self):
    return '(%s %s)' % (str(self.op), str(self.children))

class FunctionExpression(Expression):
  def __init__(self, vars, body):
    self.initialize()
    self.type = 'function'
    self.vars = vars
    self.body = body 

  def replace(self, env, bound = {}):
    for var in self.vars:
      bound[var] = True
    body = self.body.replace(env, bound)
    return FunctionExpression(self.vars, body) 
    
  def __str__(self):
    return '(lambda %s : %s)' % (str(self.vars), str(self.body))

class IfExpression(Expression):
  def __init__(self, cond, true, false):
    self.initialize()
    self.type = 'if'
    self.cond = cond
    self.true = true
    self.false = false

  def replace(self, env, bound = {}):
    cond = self.cond.replace(env, bound)
    true = self.true.replace(env, bound)
    false = self.false.replace(env, bound)
    return IfExpression(cond, true, false)
  
  def __str__(self):
    return '(if %s then %s else %s)' % (str(self.cond), str(self.true), str(self.false))

class LetExpression(Expression):
  def __init__(self, bindings, body):
    self.initialize()
    self.type = 'let'
    self.vars = []
    self.expressions = []
    for (var, expr) in bindings:
      self.vars.append(var)
      self.expressions.append(expr)
    self.body = body

  def replace(self, env, bound = {}):
    expressions = [x.replace(env, bound) for x in self.expressions]
    for var in self.vars:
      bound[var] = True
    body = self.body.replace(env, bound)
    return LetExpression([(self.vars[i], expressions[i]) for i in range(len(expressions))], body) 

  def __str__(self):
    return '(let %s = %s in %s)' % (str(self.vars), str(self.expressions), str(self.body))

class OpExpression(Expression):
  def __init__(self, op, children):
    self.initialize()
    self.type = op
    self.children = children 

  def replace(self, env, bound = {}):
    children = [x.replace(env, bound) for x in self.children]
    return OpExpression(self.type, children)
  
  def __str__(self):
    if len(self.children) == 1:
      return self.type + '(' + str(self.children[0]) + ')'
      
    return self.type.join(['(' + str(x) + ')' for x in self.children])
    # return self.type +  '(' + ','.join([str(x) for x in self.children]) + ')'

def var(v):
  return VarExpression(v) 

def op(operator, children):
  return OpExpression(operator, children) 

def ifelse(ifvar, truevar, falsevar):
  return IfExpression(ifvar, truevar, falsevar)

def apply(f, args = []):
  return ApplyExpression(f, args)

def function(vars, body):
  return FunctionExpression(vars, body)

def let(letmap, body):
  return LetExpression(letmap, body)
  ## version of let which doesn't allow recursion
  #vars = []
  #args = []
  #for (var, arg) in letmap:
  #  vars.append(var)
  #  args.append(arg)
  #return apply(function(vars, body), args)

def negation(expr):
  return OpExpression('~', [expr])

def disjunction(exprs):
  return OpExpression('|', exprs) 

def conjunction(exprs):
  return OpExpression('&', exprs)

### Values ###

def constant(v):
  return ConstExpression(v)

def num_expr(c):
  return constant(NumValue(c))

def int_expr(c):
  return constant(IntValue(c))

def nat_expr(c):
  return constant(NatValue(c))

def bool_expr(b):
  return constant(BoolValue(b))

def xrp(xrp):
  return constant(XRPValue(xrp))

### DISTRIBUTIONS ### 

bernoulli_args_xrp = ConstExpression(XRPValue(bernoulli_args_XRP()))
def bernoulli(p):
  return ApplyExpression(bernoulli_args_xrp, [p])

beta_args_xrp = ConstExpression(XRPValue(beta_args_XRP()))
def beta(a, b): 
  return ApplyExpression(beta_args_xrp, [a, b])

gamma_args_xrp = ConstExpression(XRPValue(gamma_args_XRP()))
def gamma(a, b): 
  return ApplyExpression(gamma_args_xrp, [a, b])

uniform_args_xrp = ConstExpression(XRPValue(uniform_args_XRP()))
def uniform(n = None):
  if n is None:
    return beta(int_expr(1), int_expr(1))
  else:
    return ApplyExpression(uniform_args_xrp, [n])

gaussian_args_xrp = ConstExpression(XRPValue(gaussian_args_XRP()))
def gaussian(mu, sigma):
  return ApplyExpression(gaussian_args_xrp, [mu, sigma])

