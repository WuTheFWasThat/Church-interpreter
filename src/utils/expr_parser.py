from engine.directives import *
import utils.infertools as infertools 
from utils.format import table_to_string
import time

def parse_token(s, i = 0):
    delim = ['(', ')', '[', ']', ',']
    while s[i] == ' ':
      i += 1
      if i == len(s):
        return ('', i)
    c = s[i]
    if c in delim:
      return (c, i + 1)
    else:
      j = i + 1
      while (j < len(s)):
        d = s[j]
        if (d in delim) or (d == ' '):
          break
        j += 1
      return (s[i:j], j)

def parse_integer(s, i):
  (token, i) = parse_token(s, i)
  try:
    integer = int(token)
  except:
    raise Exception("Expected integer, got %s" % token)
  return (integer, i)

def parse_expr_list(s, i):
    (token, j) = parse_token(s, i)
    expr_list = []
    while token != ')':
      (expr, i) = parse_expression(s, i)
      expr_list.append(expr)
      (token, j) = parse_token(s, i)
    return (expr_list, i)

def parse_if(s, i):
    (cond_expr, i) = parse_expression(s, i)
    (true_expr, i) = parse_expression(s, i)
    (false_expr, i) = parse_expression(s, i)
    expr = ifelse(cond_expr, true_expr, false_expr)
    return (expr, i)

def parse_noisy(s, i):
    (observation, i) = parse_expression(s, i)
    (noise, i) = parse_expression(s, i)
    expr = apply(var('bernoulli'), [ifelse(observation, int_expr(1), noise)])
    return (expr, i)

def parse_apply(s, i):
    (op_expression, i) = parse_expression(s, i)
    (expr_list, i) = parse_expr_list(s, i)
    return (apply(op_expression, expr_list), i)

def parse_lambda(s, i):
    (token, i) = parse_token(s, i)
    assert token == '('
    vars_list = []
    (token, i) = parse_token(s, i)
    while token != ')':
      vars_list.append(token)
      (token, i) = parse_token(s, i)
    assert token == ')'
    (body_expr, i) = parse_expression(s, i)
    return (function(vars_list, body_expr), i)

def parse_let(s, i):
    (token, i) = parse_token(s, i)
    assert token == '('
    letmap = []
    (token, i) = parse_token(s, i)
    while token != ')':
      assert token == '('
      (var, i) = parse_token(s, i)
      (expr, i) = parse_expression(s, i)
      letmap.append((var, expr))
      (token, i) = parse_token(s, i)
      assert token == ')'
      (token, i) = parse_token(s, i)
    assert token == ')'
    (body_expr, i) = parse_expression(s, i)
    return (let(letmap, body_expr), i)

def parse_op(s, i, operator):
    if operator == 'and':
      operator = '&'
    elif operator == 'or':
      operator = '|'
    elif operator == 'xor':
      operator = '^'
    elif operator == 'not':
      operator = '~'
    (children, i) = parse_expr_list(s, i)
    return (op(operator, children), i)

def parse_value_token(token):
  try:
    intval = int(token)
    if intval >= 0:
      val = NatValue(intval)
    else:
      val = IntValue(intval)
  except:
    try:
      floatval = float(token)
      val = NumValue(floatval)
    except:
      if token == 'False':
        val = BoolValue(False)
      elif token == 'True':
        val = BoolValue(True)
      else:
        raise Exception("Invalid value (Note:  Procedures and XRPs not parseable)")
  return val

def parse_value(s, i):
  (token, i) = parse_token(s, i)
  return (parse_value_token(token), i)

def parse_expression(s, i):
    (token, i) = parse_token(s, i)
    if len(token) < 0:
      raise Exception("No token")
    if token == '(':
      (token, j) = parse_token(s, i)
      if token == 'if':
        (expr, i) = parse_if(s, j)
      elif token == 'lambda':
        (expr, i) = parse_lambda(s, j)
      elif token == 'let':
        (expr, i) = parse_let(s, j)
      elif token in ['+', '-', '*', '/', \
                     '&', '|', '^', '~', \
                     'and', 'or', 'xor', 'not', \
                     '=', '<', '<=', '>', '>=']:
        (expr, i) = parse_op(s, j, token)
      elif token == 'noisy':
        (expr, i) = parse_noisy(s, j)
      else:
        (expr, i) = parse_apply(s, i)
      (token, i) = parse_token(s, i)
      assert token == ')'
    else:
      try:
        val = parse_value_token(token)
        expr = constant(val)
      except:
        expr = var(token)
    return (expr, i)


def parse_directive(s):
  ret_str = 'done'
  (token, i) = parse_token(s, 0)
  if token == 'assume':
    (var, i) = parse_token(s, i)
    (expr, i) = parse_expression(s, i)
    (val, id) = assume(var, expr)
    ret_str = 'value: ' + val.__str__() + '\nid: ' + str(id)
  elif token == 'observe':
    (expr, i) = parse_expression(s, i)
    (val, i) = parse_value(s, i)
    id = observe(expr, val)
    ret_str = 'id: ' + str(id)
  elif token == 'predict':
    (expr, i) = parse_expression(s, i)
    (val, id) = predict(expr)
    ret_str = 'value: ' + val.__str__() + '\nid: ' + str(id)
  elif token == 'forget':
    (id, i) = parse_integer(s, i)
    forget(id)
    ret_str = 'forgotten'
  elif token == 'infer':
    infer()
  elif token == 'infer_many':
    (expression, i) = parse_expression(s, i)
    (niters, i) = parse_integer(s, i)
    (burnin, i) = parse_integer(s, i)
    t = time.time()
    d = infertools.infer_many(expression, niters, burnin)
    t = time.time() - t
    ret_str = '\n'
    table = []
    for val in d:
      p = d[val]
      table.append([val.__str__(), str(p)])
    ret_str = table_to_string(table, ['Value', 'Count'])
    ret_str += '\nTime taken (seconds): ' + str(t)
  elif token == 'clear':
    reset()
    ret_str = 'cleared'
  elif token == 'report_value':
    (id, i) = parse_integer(s, i)
    ret_str = 'value: ' + report_value(id)
  elif token == 'report_directives':
    (directive_type, i) = parse_token(s, i)
    directives_report = report_directives(directive_type)
    ret_str = table_to_string(directives_report, ['id', 'directive', 'value'])
  else:
    raise Exception("Invalid directive")
  return ret_str
