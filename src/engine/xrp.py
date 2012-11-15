from values import *
import math
from utils.rexceptions import RException

# HELPERS

def check_prob(val):
  if not 0 <= val <= 1:
    raise RException("Value %s is not a valid probability" % str(val))
  if val == 0:
    return 2**(-32)
  elif val == 1:
    return 1 - 2**(-32)
  return val

def check_pos(val):
  if not 0 < val:
    raise RException("Value %s is not positive" % str(val))

def sum(array):
  ans = 0
  for x in array:
    ans += x
  return ans

# taken from Wikipedia's page on Lanczos approximation, but only works on real numbers

def math_gamma(z):
  g = 7
  p = [0.99999999999980993, 676.5203681218851, -1259.1392167224028,
       771.32342877765313, -176.61502916214059, 12.507343278686905,
       -0.13857109526572012, 9.9843695780195716e-6, 1.5056327351493116e-7]
 
  if z < 0.5:
      return math.pi / (math.sin(math.pi * z) * math_gamma(1-z))
  else:
      z -= 1
      x = p[0]
      for i in range(1, g+2):
          x += p[i]/(z+i)
      t = z + g + 0.5
      return math.sqrt(2*math.pi) * math.pow(t, (z+0.5)) * math.exp(-t) * x

def dirichlet(params):
  sample = [rrandom.random.gammavariate(a,1) for a in params]
  z = sum(sample) + 0.0
  return [v/z for v in sample]

def sample_categorical(probs):
  (i, v) = (0, rrandom.random.random())
  while probs[i] < v:
    v -= probs[i]
    i += 1
  return i

# GENERALLY USEFUL XRPs

class categorical_no_args_XRP(XRP):
  def __init__(self, probs):
    self.deterministic = False
    self.state = None
    self.probs = [check_prob(p) for p in probs]
    if not .999 <= sum(self.probs) <= 1.001:
      raise RException("Categorical probabilities must sum to 1")
    self.n = len(self.probs)
    return
  def apply(self, args = None):
    i = sample_categorical(self.probs)
    if args != None and len(args) != 0:
      raise RException("categorical_no_args_XRP has no need to take arguments")
    return IntValue(i)
  def prob(self, val, args = None):
    if args != None and len(args) != 0:
      raise RException("categorical_no_args_XRP has no need to take arguments")
    if not 0 <= val.int < self.n:
      raise RException("Categorical should only return values between 0 and %d" % self.n)
    log_prob = math.log(self.probs[val.int])
    return log_prob
  def __str__(self):
    return 'categorical(%f, %f)' % (self.mu, self.sigma)

class make_symmetric_categorical_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    n = args[0].num
    return XRPValue(categorical_no_args_XRP([1 / (n + 0.0)] * n)) 
  def __str__(self):
    return 'make_symmetric_categorical_XRP'

class gaussian_args_XRP(XRP):
  def __init__(self):
    self.deterministic = False
    return
  def apply(self, args = None):
    (mu, sigma) = (args[0].num, args[1].num)
    check_pos(sigma)
    return NumValue(rrandom.random.normalvariate(mu, sigma))
  def prob(self, val, args = None):
    (mu , sigma) = (args[0].num, args[1].num + 0.0)
    check_pos(sigma)
    log_prob = - math.pow((val.num - mu) / sigma, 2)/ 2.0 - math.log(sigma) - math.log(2 * math.pi) / 2.0
    return log_prob
  def __str__(self):
    return 'normal'

class gaussian_no_args_XRP(XRP):
  def __init__(self, mu, sigma):
    self.deterministic = False
    check_pos(sigma)
    (self.mu , self.sigma) = (mu, sigma + 0.0)
    self.prob_help = - math.log(sigma) - math.log(2 * math.pi) / 2.0
    return
  def apply(self, args = None):
    if args is not None and len(args) != 0:
      raise RException('gaussian_no_args_XRP has no need to take in arguments %s' % str(args))
    return NumValue(rrandom.random.normalvariate(self.mu, self.sigma))
  def prob(self, val, args = None):
    if args is not None and len(args) != 0:
      raise RException('gaussian_no_args_XRP has no need to take in arguments %s' % str(args))
    log_prob = self.prob_help - math.pow((val.num - self.mu) / self.sigma, 2) / 2.0 
    return log_prob
  def __str__(self):
    return 'gaussian(%f, %f)' % (self.mu, self.sigma)

class make_gaussian_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    (mu,sigma) = (args[0].num, args[1].num)
    check_pos(sigma)
    return XRPValue(gaussian_no_args_XRP(mu, sigma)) 
  def __str__(self):
    return 'gaussian_XRP'

class array_XRP(XRP):
  def __init__(self, array):
    self.deterministic = True
    self.array = array
    self.n = len(self.array)
    return
  def apply(self, args = None):
    if len(args) != 1:
      raise RException("Should have 1 argument, not %d" % len(args))
    i = args[0].nat
    if not 0 <= i < self.n:
      raise RException("Index must from 0 to %d - 1" % self.n)
    return self.array[i]
  def prob(self, val, args = None):
    if len(args) != 1:
      raise RException("Should have 1 argument, not %d" % len(args))
    i = args[0].nat
    if not 0 <= i < self.n:
      raise RException("Index must from 0 to %d - 1" % self.n)
    if val != self.array[i]:
      raise RException("Array at index %d should've been %s" % (i, val.__str__()))
    return 0
  def __str__(self):
    return ('array(%s)' % str(self.array))

class dirichlet_args_XRP(XRP):
  def __init__(self):
    self.deterministic = False
    return
  def apply(self, args = None):
    for arg in args:
      check_pos(arg.num)
    probs = [NumValue(p) for p in dirichlet([arg.num for arg in args])]
    return XRPValue(array_XRP(probs))
  def prob(self, val, args = None):
    if val.type != 'xrp':
      raise RException("Returned value should have been an XRP")
    probs = [x.num for x in val.xrp.state]
    for prob in probs:
      check_prob(prob)
    n = len(args)
    if len(probs) != n:
      raise RException("Number of arguments, %d, should've been the dimension %d" % (n, len(probs)))

    alpha = 0
    for alpha_i in args:
      check_pos(alpha_i.num)
      alpha += alpha_i.num

    return math.log(math_gamma(alpha)) + sum([(args[i].num - 1) * math.log(probs[i]) for i in range(n)]) \
           - sum([math.log(math_gamma(args[i].num)) for i in range(n)])

  def __str__(self):
    return 'dirichlet'

class dirichlet_no_args_XRP(XRP):
  def __init__(self, args):
    self.deterministic = False
    self.alphas = args
    self.alpha = 0
    for alpha_i in self.alphas:
      check_pos(alpha_i)
      self.alpha += alpha_i
    return
  def apply(self, args = None):
    if args is not None and len(args) != 0:
      raise RException('dirichlet_no_args_XRP has no need to take in arguments %s' % str(args))
    probs = [NumValue(p) for p in dirichlet(self.alphas)]
    return XRPValue(array_XRP(probs))
  def prob(self, val, args = None):
    if args is not None and len(args) != 0:
      raise RException('dirichlet_no_args_XRP has no need to take in arguments %s' % str(args))
    if val.type != 'xrp':
      raise RException('dirichlet_no_args_XRP should return an XRP')
    probs = [x.num for x in val.xrp.array]
    for prob in probs:
      check_prob(prob)

    n = len(self.alphas)
    assert len(probs) == n

    return math.log(math_gamma(self.alpha)) + sum([(self.alphas[i] - 1) * math.log(probs[i]) for i in range(n)]) \
           - sum([math.log(math_gamma(self.alphas[i])) for i in range(n)])
  def __str__(self):
    return 'dirichlet(%s)' % str(self.alphas)

class make_symmetric_dirichlet_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    if len(args) != 2:
      raise RException("Symmetric dirichlet generator takes two arguments, n and alpha")
    (n, alpha) = (args[0], args[1])
    return XRPValue(dirichlet_no_args_XRP([alpha.num] * n.nat)) 
  def __str__(self):
    return 'dirichlet_XRP'

class make_dirichlet_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    return XRPValue(dirichlet_no_args_XRP([arg.num for arg in args])) 
  def __str__(self):
    return 'dirichlet_XRP'

class beta_args_XRP(XRP):
  def __init__(self):
    self.deterministic = False
    return
  def apply(self, args = None):
    (a,b) = (args[0].num, args[1].num)
    check_pos(a)
    check_pos(b)
    return NumValue(rrandom.random.betavariate(a, b))
  def prob(self, val, args = None):
    (a , b) = (args[0].num, args[1].num)
    check_pos(a)
    check_pos(b)
    v = check_prob(val.num)
    return math.log(math_gamma(a + b)) + (a - 1) * math.log(v)  + (b - 1) * math.log(1 - v) \
           - math.log(math_gamma(a)) - math.log(math_gamma(b))
  def __str__(self):
    return 'beta'

class beta_no_args_XRP(XRP):
  def __init__(self, a, b):
    self.deterministic = False
    check_pos(a)
    check_pos(b)
    self.a, self.b = a, b 
    self.prob_help = math.log(math_gamma(a + b)) - math.log(math_gamma(a)) - math.log(math_gamma(b))
    return
  def apply(self, args = None):
    if args is not None and len(args) != 0:
      raise RException('beta_no_args_XRP has no need to take in arguments %s' % str(args))
    return NumValue(rrandom.random.betavariate(self.a, self.b))
  def prob(self, val, args = None):
    if args is not None and len(args) != 0:
      raise RException('beta_no_args_XRP has no need to take in arguments %s' % str(args))
    v = check_prob(val.num)
    return self.prob_help + (self.a - 1) * math.log(v) + (self.b - 1) * math.log(1 - v) 
  def __str__(self):
    return 'beta(%d, %d)' % (self.a, self.b)

class make_beta_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    (a,b) = (args[0].num, args[1].num)
    check_pos(a)
    check_pos(b)
    return XRPValue(beta_no_args_XRP(a, b)) 
  def __str__(self):
    return 'beta_XRP'

class gamma_args_XRP(XRP):
  def __init__(self):
    self.deterministic = False
    return
  def apply(self, args = None):
    (a,b) = (args[0].num, args[1].num)
    check_pos(a)
    check_pos(b)
    return NumValue(rrandom.random.gammavariate(a, b))
  def prob(self, val, args = None):
    (a , b) = (args[0].num, args[1].num)
    check_pos(a)
    check_pos(b)
    check_pos(val.num)
    if val.num == 0:
      val.num = .0000000000000001
    return (a-1) * math.log(val.num) - ((val.num + 0.0) / b) - math.log(math_gamma(a)) - a * math.log(b)
  def __str__(self):
    return 'gamma'

class gamma_no_args_XRP(XRP):
  def __init__(self, a, b):
    self.deterministic = False
    check_pos(a)
    check_pos(b)
    self.a, self.b = a, b 
    self.prob_help = - math.log(math_gamma(a)) - a * math.log(b)
    return
  def apply(self, args = None):
    if args is not None and len(args) != 0:
      raise RException('gamma_no_args_XRP has no need to take in arguments %s' % str(args))
    return NumValue(rrandom.random.gammavariate(self.a, self.b))
  def prob(self, val, args = None):
    if args is not None and len(args) != 0:
      raise RException('gamma_no_args_XRP has no need to take in arguments %s' % str(args))
    check_pos(val.num)
    if val.num == 0:
      val.num = .0000000000000001
    return self.prob_help + (self.a - 1) * math.log(val.num) - ((val.num + 0.0) / self.b)
  def __str__(self):
    return 'gamma(%d, %d)' % (self.a, self.b)

class make_gamma_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    (a,b) = (args[0].num, args[1].num)
    check_pos(a)
    check_pos(b)
    return XRPValue(gamma_no_args_XRP(a, b)) 
  def __str__(self):
    return 'gamma_XRP'

class bernoulli_args_XRP(XRP):
  def __init__(self):
    self.deterministic = False
    return
  def apply(self, args = None):
    p = args[0].num
    p = check_prob(p)
    return BoolValue(rrandom.random.random() < p)
  def prob(self, val, args = None):
    p = args[0].num
    p = check_prob(p)
    if val.bool:
      return math.log(p)
    else:
      return math.log(1.0 - p)
  def __str__(self):
    return 'bernoulli'

class bernoulli_no_args_XRP(XRP):
  def __init__(self, p):
    self.deterministic = False
    self.p = p
    p = check_prob(p)
    return
  def apply(self, args = None):
    if args is not None and len(args) != 0:
      raise RException('bernoulli_no_args_XRP has no need to take in arguments %s' % str(args))
    return BoolValue(rrandom.random.random() < self.p)
  def prob(self, val, args = None):
    if args is not None and len(args) != 0:
      raise RException('bernoulli_no_args_XRP has no need to take in arguments %s' % str(args))
    if val.bool:
      return math.log(self.p)
    else:
      return math.log(1.0 - self.p)
  def __str__(self):
    return 'bernoulli(%f)' % self.p

class make_bernoulli_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    p = args[0].num
    p = check_prob(p)
    return XRPValue(bernoulli_no_args_XRP(p)) 
  def __str__(self):
    return 'bernoulli_XRP'

class uniform_args_XRP(XRP):
  def __init__(self):
    self.deterministic = False
    return
  def apply(self, args = None):
    n = args[0].nat
    return NatValue(rrandom.random.randbelow(n))
  def prob(self, val, args = None):
    n = args[0].nat
    assert 0 <= val.nat < n
    return -math.log(n)
  def __str__(self):
    return 'uniform'

class uniform_no_args_XRP(XRP):
  def __init__(self, n):
    self.deterministic = False
    self.n = n
    return
  def apply(self, args = None):
    if args is not None and len(args) != 0:
      raise RException('uniform_no_args_XRP has no need to take in arguments %s' % str(args))
    return NatValue(rrandom.random.randbelow(self.n))
  def prob(self, val, args = None):
    if args is not None and len(args) != 0:
      raise RException('uniform_no_args_XRP has no need to take in arguments %s' % str(args))
    assert 0 <= val.nat < self.n
    return -math.log(self.n)
  def __str__(self):
    return 'uniform(%d)' % self.n

class make_uniform_XRP(XRP):
  def __init__(self):
    self.deterministic = True
    return
  def apply(self, args = None):
    n = args[0].nat
    return XRPValue(uniform_no_args_XRP(n)) 
  def __str__(self):
    return 'uniform_XRP'

### MORE SPECIFIC XRPs

class beta_bernoulli_1(XRP):
  def __init__(self, start_state = (1, 1)):
    self.deterministic = False
    (a, b) = start_state
    self.p = check_prob(rrandom.random.betavariate(a, b))
    self.true_log_p = math.log(self.p)
    self.false_log_p = math.log(1.0 - self.p)
  def apply(self, args = None):
    return BoolValue((rrandom.random.random() < self.p))
  def prob(self, val, args = None):
    if val.bool:
      return self.true_log_p
    else:
      return self.false_log_p
  def __str__(self):
    return 'beta_bernoulli'

class beta_bernoulli_2(XRP):
  def __init__(self, start_state = (1, 1)):
    self.deterministic = False
    (self.h, self.t) = start_state
  def apply(self, args = None):
    if (self.h | self.t == 0):
      val = (rrandom.random.random() < 0.5)
    else:
      val = (rrandom.random.random() * (self.h + self.t) < self.h)
    return BoolValue(val)
  def incorporate(self, val, args = None):
    if val.bool:
      self.h += 1
    else:
      self.t += 1
  def remove(self, val, args = None):
    if val.num:
      assert self.h > 0
      self.h -= 1
    else:
      assert self.t > 0
      self.t -= 1
  def prob(self, val, args = None):
    if (self.h | self.t) == 0:
      return - math.log(2)
    else:
      if val.num:
        return math.log(self.h) - math.log(self.h + self.t)
      else:
        return math.log(self.t) - math.log(self.h + self.t)
  def __str__(self):
    return 'beta_bernoulli'

### TOPIC MODELS

# fully collapsed topic model
class topic_model_XRP(XRP):
  def __init__(self, ntopics, alpha_topics, nwords, alpha_words):
    self.deterministic = False
    self.state = None
    (self.ntopics, self.alpha_topics, self.nwords, self.alpha_words) = (ntopics, alpha_topics, nwords, alpha_words)
    self.topicdist = sample_dirichlet([alpha_topics] * ntopics)
    self.worddist = [sample_dirichlet([alpha_words] * nwords) for i in range(ntopics)]
    self.wordlogprobs = [sum(self.topicdist[j] * self.worddist[j][i] for j in range(ntopics)) for i in xrange(nwords)]
    return
  def apply(self, args = None):
    topic = sample_categorical(self.topicdist)
    assert 0 <= topic < self.ntopics
    word = sample_categorical(self.worddist[topic])
    assert 0 <= word < self.nwords
    return IntValue(word)
  def prob(self, val, args = None):
    assert 0 <= val.int <= self.nwords
    return self.wordlogprobs[val.int]
  def __str__(self):
    return 'topic model'

class make_topic_model_XRP(XRP):
  def __init__(self):
    self.deterministic = False # params chosen in the constructor
    self.state = None
    return
  def apply(self, args = None):
    (ntopics, alpha_topics, nwords, alpha_words) = args
    return XRPValue(topic_model_XRP(ntopics.int, alpha_topics.float, nwords.int, alpha_words.float)) 
  def prob(self, val, args = None):
    return 0
  def __str__(self):
    return 'make_topic_model_XRP'

# half collapsed topic model
#class word_dist_XRP(XRP):
#  def __init__(self, ntopics, alpha_topics, nwords, alpha_words):
#    self.deterministic = False
#    self.state = None
#    (self.ntopics, self.alpha_topics, self.nwords, self.alpha_words) = (ntopics, alpha_topics, nwords, alpha_words)
#    self.topicdist = sample_dirichlet([alpha_topics] * ntopics)
#    self.worddist = [sample_dirichlet([alpha_words] * nwords) for i in range(ntopics)]
#    self.wordlogprobs = [sum(self.topicdist[j] * self.worddist[j][i] for j in range(ntopics)) for i in xrange(nwords)]
#    return
#  def apply(self, args = None):
#    topic = sample_categorical(self.topicdist)
#    assert 0 <= topic < self.ntopics
#    word = sample_categorical(self.worddist[topic])
#    assert 0 <= word < self.nwords
#    return IntValue(word)
#  def prob(self, val, args = None):
#    assert 0 <= val.val <= self.nwords
#    return self.wordlogprobs[val.val]
#  def __str__(self):
#    return 'topic model'
#
#class make_word_dist_XRP(XRP):
#  def __init__(self):
#    self.deterministic = False # params chosen in the constructor
#    self.state = None
#    return
#  def apply(self, args = None):
#    (nwords, alpha_words) = args
#    return XRPValue(word_dist_XRP(nwords.val, alpha_words.val)) 
#  def prob(self, val, args = None):
#    return 0
#  def __str__(self):
#    return 'make_word_dist_XRP'
#
#class topic_dist_XRP(XRP):
#  def __init__(self, ntopics, alpha_topics):
#    self.deterministic = False
#    self.state = None
#    (self.ntopics, self.alpha_topics) = (ntopics, alpha_topics)
#    self.topicdist = sample_dirichlet([alpha_topics] * ntopics)
#    return
#  def apply(self, args = None):
#    topic = sample_categorical(self.topicdist)
#    assert 0 <= topic < self.ntopics
#    word = sample_categorical(self.worddist[topic])
#    assert 0 <= word < self.nwords
#    return IntValue(word)
#  def prob(self, val, args = None):
#    assert 0 <= val.val <= self.nwords
#    return self.wordlogprobs[val.val]
#  def __str__(self):
#    return 'topic_dist_XRP'
#
#class make_topic_dist_XRP(XRP):
#  def __init__(self):
#    self.deterministic = False # params chosen in the constructor
#    self.state = None
#    return
#  def apply(self, args = None):
#    (ntopics, alpha_topics) = args
#    return XRPValue(topic_dist_XRP(ntopics.val, alpha_topics.val)) 
#  def prob(self, val, args = None):
#    return 0
#  def __str__(self):
#    return 'make_topic_dist_XRP'
#
