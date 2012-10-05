from directives import *
import matplotlib.pyplot as plt 
import time

""" Dictionary -> distribution """

def count_up(list):
  d = {}
  for x in list:
    if x in d:
      d[x] += 1
    else:
      d[x] = 1
  return d

def average(list):
  return sum(list) / (0.0 + len(list))

def standard_deviation(list):
  avg = average(list)
  variance = (sum((x-avg)**2 for x in list)) / (0.0 + len(list))
  return variance**0.5

def normalize(dict):
  z = sum([dict[val] for val in dict])
  for val in dict:
    dict[val] = dict[val] / (z + 0.0)
  return dict

def merge_counts(d1, d2):
  d = {} 
  for x in d1:
    d[x] = d1[x]
  for x in d2:
    if x in d:
      d[x] += d2[x]
    else:
      d[x] = d2[x]
  return d

""" Inference routines """

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

def infer_many(name, niter = 1000, burnin = 100, printiters = 0):
  if name in globals.mem.vars:
    expr = globals.mem.vars[name]
  else:
    warnings.warn('%s is not defined' % str(name))

  if globals.use_traces:
    rerun(True)
  dict = {}
  for n in xrange(niter):
    if printiters > 0 and n % printiters == 0: 
      print n, "iters"

    # re-draw from prior
    for t in xrange(burnin):
      infer()

    val = evaluate(name, globals.env, reflip = False, stack = [name])
    if val in dict:
      dict[val] += 1
    else:
      dict[val] = 1 

  return dict 

def follow_prior(names, niter = 1000, burnin = 100, printiters = 0):
  rerun(True)
  dict = {}

  for t in xrange(burnin):
    infer()

  for name in names:
    #if name in globals.mem.vars:
    #  expr = globals.mem.vars[name]
    #else:
    #  warnings.warn('%s is not defined' % str(name))
    assert name not in set(['TIME'])
    dict[name] = []
  dict['TIME'] = []
  
  for n in xrange(niter):
    if printiters > 0 and n % printiters == 0: 
      print n, "iters"
    t = time.time()
    infer()

    for name in names:
      val = evaluate(name, globals.env, reflip = False, stack = [name])
      if val.type != 'procedure' and val.type != 'xrp': 
        dict[name].append(val)
    t = time.time() - t
    dict['TIME'].append(t)

  return dict 

def sample_prior(names, niter = 1000, printiters = 0):
  dict = {}

  for name in names:
    #if name in globals.mem.vars:
    #  expr = globals.mem.vars[name]
    #else:
    #  warnings.warn('%s is not defined' % str(name))
    assert name not in set(['TIME'])
    dict[name] = {}
  dict['TIME'] = {}

  for n in xrange(niter):
    if printiters > 0 and n % printiters == 0: 
      print n, "iters"
    t = time.time()
    rerun(True)
    for name in names:
      val = evaluate(name, globals.env, reflip = True, stack = [name])
      if val.type != 'procedure' and val.type != 'xrp': 
        if val in dict[name]:
          dict[name][val] += 1
        else:
          dict[name][val] = 1
    t = time.time() - t
    if t in dict['TIME']:
      dict['TIME'][t] += 1
    else:
      dict['TIME'][t] = 1

  return dict 

def test_prior(niter = 1000, burnin = 100):
  expressions = []
  varnames = []

  for (varname, expr) in globals.mem.assumes:
    assert varname not in set(['TIME'])
    expressions.append(expr)
    varnames.append(varname)
  # TODO : get all the observed variables
  # 
  #for hashval in globals.mem.observes:
  #  (expr, obs_val) = globals.mem.observes[hashval] 
  #  expressions.append(expr)

  e1 = sample_prior(expressions, niter)
  e2 = follow_prior(expressions, niter, burnin)
  d1 = {}
  d2 = {}
  for i in xrange(len(varnames)):
    expr = expressions[i]
    assert expr in e1
    assert expr in e2
    d1[varnames[i]] = e1[expr]
    d2[varnames[i]] = count_up(e2[expr])
  d1['TIME'] = e1['TIME']
  d2['TIME'] = count_up(e2['TIME'])
  return (d1, d2)

def test_prior_bool(d, varname):
  return abs(d[0][varname][False] - d[1][varname][False]) / (d[0][varname][False] + d[0][varname][True])

def test_prior_L0(d, varname, start, end, bucketsize):
  (d1, d2) = (d[0][varname], d[1][varname])
  c1 = get_cdf(d1, start, end, bucketsize, True)
  c2 = get_cdf(d2, start, end, bucketsize, True)
  a = L0distance(c1, c2)
  return a

""" NOISE """

def noisy(expression, error):
  return bernoulli(ifelse(expression, 1, error))

""" OUTPUT MANIPULATION """

def get_pdf(valuedict, start, end, bucketsize, normalizebool = True):
  if normalizebool:
    valuedict = normalize(valuedict)
  numbuckets = int(math.floor((end - start) / bucketsize))
  density = [0] * numbuckets
  for value in valuedict:
    if not start <= value.val <= end:
      warnings.warn('value %s is not in the interval [%s, %s]' % (str(value), str(start), str(end)))
      continue
    index = int(math.floor((value.val - start) / bucketsize))
    density[index] += valuedict[value.val]
  return density

def get_cdf(valuedict, start, end, bucketsize, normalizebool = True):
  numbuckets = int(math.floor((end - start) / bucketsize))
  density = get_pdf(valuedict, start, end, bucketsize, normalizebool)
  cumulative = [0]
  for i in range(numbuckets):
    cumulative.append(cumulative[-1] + density[i])
  if normalizebool:
    assert 0.999 < cumulative[-1] < 1.001
  return cumulative

""" PLOTTING TOOLS """

def plot(xs, ys, name = 'graphs/plot.png', minx = None, maxx = None, miny = None, maxy = None):
  if minx is None: minx = xs[0]
  if maxx is None: maxx = xs[-1]
  if miny is None: miny = min(ys)
  if maxy is None: maxy = max(ys)
  plt.axis([minx, maxx, miny, maxy])
  plt.plot(xs, ys)
  plt.savefig(name)
#  plt.close()

def plot_dist(ys, start, end, bucketsize, name = 'graphs/plot.png', ymax = None):
  numbuckets = int(math.floor((end - start) / bucketsize))
  xs = [start + i * bucketsize for i in range(numbuckets+1)]
  plot(xs, ys, name, start, end, 0, ymax)

def plot_pdf(valuedict, start, end, bucketsize, name = 'graphs/plot.png', ymax = None):
  plot_dist(get_pdf(valuedict, start, end, bucketsize), start + (bucketsize / 2.0), end - (bucketsize / 2.0), bucketsize, name, ymax)

def plot_cdf(valuedict, start, end, bucketsize, name = 'graphs/plot.png'):
  plot_dist(get_cdf(valuedict, start, end, bucketsize), start, end, bucketsize, name, 1)

def plot_beta_cdf(a, b, bucketsize, name = 'graphs/betaplot.png'):
  plot_dist(get_beta_cdf(a, b, bucketsize), 0, 1, bucketsize, name, 1)

def get_beta_cdf(a, b, bucketsize):
  assert type(a) == type(b) == int

  coeffs = [math.gamma(a+b) / (math.gamma(i + 1) * math.gamma(a+b-i)) for i in range(a, a+b)]

  numbuckets = int(math.floor(1.0 / bucketsize))
  xs = [i * bucketsize for i in range(numbuckets)]

  cumulative = [0]
  for x in xs:
    ppows = [1]
    npows = [1]
    for i in range(a + b):
      ppows.append(ppows[-1] * x)
      npows.append(npows[-1] * (1-x))
    sum = 0
    for i in range(a, a+b):
      sum += coeffs[i-a] * ppows[i] * npows[a + b - 1 - i]
    cumulative.append(sum)
  return cumulative

def format(list, format):
  return [ format % x for x in list]

def plotnames(names, plotname = 'plotnames'):
  for name in names:
    plot(range(niter), dict[name], 'graphs/' + plotname + '-' + name + '.png')

""" DISTANCE MEASURES """

def L0distance(cdf1, cdf2):  # Kolmogorov-Smirnov test 
  return max(abs(cdf1[i] - cdf2[i]) for i in xrange(len(cdf1)))

def L1distance(cdf2, cdf1):
  return sum(abs(cdf1[i] - cdf2[i]) for i in xrange(len(cdf1)))

def KLdivergence(d, pdf):
  d = normalize(d)
  kl = 0
  for x in d:
    kl += d[x] * (log(d[x]) - log(pdf(x)))
  return kl

def perplexity(d, pdf):
  d = normalize(d)
  ans = 0
  for x in d:
    ans += d[x] * log(pdf(x))
  return ans
