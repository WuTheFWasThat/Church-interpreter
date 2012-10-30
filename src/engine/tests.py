from mem import *
from infertools import * 
from time import *

import unittest

test_expressions = True
test_recursion = True
test_mem = True

test_HMM = False
test_bayes_nets = True
test_two_layer_nets = False

test_xor = False 

test_tricky  = False 

# something wrong with this test
test_geometric = False 

test_DPmem = False
test_CRP = False

test_easy_mixture = False

""" TESTS """

class TestDirectives(unittest.TestCase):
  def setUp(self):
    reset()

  @unittest.skipIf(not test_expressions, "skipping test_expressions")
  def test_expressions(self):
  
    f = function(('x','y','z'), ifelse(var('x'), var('y'), var('z')))
    self.assertTrue(sample(f).type == 'procedure')
    
    g = function( ('x', 'z'), apply(f, [var('x'), constant(0), var('z')] ))
    self.assertTrue(sample(g).type == 'procedure')
    
    a = bernoulli(constant(0.5)) 
    #d = count_up([resample(a).val for i in xrange(1000)])
    #self.assertTrue(d[True] + d[False] == 1000)
    #self.assertTrue(450 < d[True] < 550)
    
    x = apply(g, [a, uniform(constant(22))])
    b = ifelse(bernoulli(constant(0.2)), beta(constant(3),constant(4)), beta(constant(4),constant(3)))
    c = (~bernoulli(constant(0.3)) & bernoulli(constant(0.4))) | bernoulli(b)
    d = function('x', ('apply', f, [a,c,var('x')]))
    e = apply( d, b)
  
    # Testing closure
    f = function(('x', 'y'), apply(var('x'), var('y')))
    g = function('x', var('x') + constant(1))
    self.assertTrue(sample(apply(f, [g, constant(21)])) == Value(22))

    assume('f', f)
    assume('g', g)
    a = let([('b', constant(1))], var('b') + constant(3))
    self.assertTrue(sample(a) == Value(4))

    b = let([('c', constant(21)), ('d', var('f'))], apply(var('d'), [var('g'), var('c')]))
    self.assertTrue(sample(b) == Value(22))


  @unittest.skipIf(not test_tricky, "skipping test_tricky")
  def test_tricky(self):
    noise_level = .01
  
    assume('make-coin', function([], apply(function('weight', function([], bernoulli(var('weight')))), beta(constant(1), constant(1)))))
  
    assume('tricky-coin', apply(var('make-coin')))
    assume('tricky-coin2', apply(var('make-coin')))
  
    assume('fair-coin', function([], bernoulli(constant(0.5))))
  
    assume('is-fair', bernoulli(constant(0.5)))
    assume('coin', ifelse(var('is-fair'), var('fair-coin'), var('tricky-coin'))) 

    d = test_prior(1000, 10)
    print d
    #self.assertTrue(test_prior_bool(d, 'is-fair') < 0.05)
  
    ## EXTENSIVE TEST

    nheads = 2
    niters, burnin = 1000, 10
  
    print infer_many('is-fair', niters, burnin)
    
    for i in xrange(nheads):
      print '\nsaw', i+1, 'heads'
      observe(noisy(apply(var('coin')), noise_level), Value(True))
      print infer_many('is-fair', niters, burnin)
  
  @unittest.skipIf(not test_CRP, "skipping test_CRP")
  def test_CRP(self):
    print " \n TESTING CHINESE RESTAURANT PROCESS XRP\n"
    
    print "CRP(1)"
    assume('crp1', CRP(1))
    print [sample(apply('crp1')) for i in xrange(10)]
    
    print "CRP(10)"
    assume('crp2', CRP(10))
    print [sample(apply('crp2')) for i in xrange(10)]
  
    assume('alpha', gamma(0.1, 20))
    assume('cluster-crp', CRP('alpha'))
    assume('get-cluster-mean', mem(function('cluster', gaussian(0, 10))))
    assume('get-cluster-variance', mem(function('cluster', gamma(0.1, 100))))
    assume('get-cluster', mem(function('id' , apply('cluster-crp'))))
    assume('get-cluster-model', mem(function('cluster', function([], gaussian(apply('get-cluster-mean', 'cluster'), apply('get-cluster-variance', 'cluster'))))))
    assume('get-datapoint', mem(function('id', gaussian(apply(apply('get-cluster-model', apply('get-cluster', 'id'))), 0.1))))
    assume('outer-noise', gamma(0.1, 10)) 
  
    print test_prior(1000, 100)
  
    #points = {} 
    #for i in xrange(100):
    #  print sample(apply('get-cluster', i)) , " : ", sample(apply('get-datapoint', i))
    #for i in xrange(1000):
    #  val = sample(apply('get-datapoint', i))
    #  if val in points:
    #    points[val] += 1
    #  else:
    #    points[val] = 1
    #plot_pdf(points, -50, 50, 0.1, name = 'graphs/crpmixturesample.png')
  
    assume('x', apply('get-datapoint', 0))
    observe(gaussian('x', let([('x', gaussian(constant(0), var('outer-noise')))], var('x') * var('x'))), Value(2.3))
    observe(gaussian(apply('get-datapoint', 1), let([('y', gaussian(0, 'outer-noise'))], var('y') * var('y'))), Value(2.2))
    observe(gaussian(apply('get-datapoint', 2), let([('y', gaussian(0, 'outer-noise'))], var('y') * var('y'))), Value(1.9))
    observe(gaussian(apply('get-datapoint', 3), let([('y', gaussian(0, 'outer-noise'))], var('y') * var('y'))), Value(2.0))
    observe(gaussian(apply('get-datapoint', 4), let([('y', gaussian(0, 'outer-noise'))], var('y') * var('y'))), Value(2.1))
  
    niters, burnin = 100, 1000
  
    print sample('x')
    print sample('x')
    a = infer_many('x', 10, 1000)
    print sample('x')
    print sample('x')
    #print sample(apply('get-datapoint', 0))
    #print sample(apply('get-datapoint', 0))
    #print sample(apply('get-datapoint', 0))
    print a
    print format(get_pdf(a, -4, 4, .5), '%0.2f') 
  
    #print 'running', niters, 'times,', burnin, 'burnin'
  
    #t = time()
    #a = infer_many('expected-mean', niters, burnin)
    #print format(get_pdf(a, -4, 4, .5), '%0.2f') 
    #print 'time taken', time() - t
  
  @unittest.skipIf(not test_HMM, "skipping test_HMM")
  def test_HMM(self):
    n = 5
    t = 20

    assume('dirichlet', constant(dirichlet_no_args_XRP([1]*n)))
    assume('get-column', mem(function('i', apply(var('dirichlet')))))
    assume('get-next-state', function('i', 
                             let([('loop', \
                                  function(['v', 'j'], \
                                           let([('w', apply(apply(var('get-column'), var('i')), var('j')))],
                                            ifelse(var('v') < var('w'), var('j'), apply(var('loop'), [var('v') - var('w'), var('j') + constant(1)]))))) \
                                 ], \
                                 apply(var('loop'), [uniform(), constant(0)])))) 
    assume('state', mem(function('i',
                                 ifelse(var('i') == constant(0), constant(0), apply(var('get-next-state'), apply(var('state'), var('i') - constant(1)))))))
  
    assume('start-state', apply(var('state'), constant(0)))
    assume('second-state', apply(var('state'), constant(t)))

    print sample(var('second-state'))

    print test_prior(10, 10)
  

  @unittest.skipIf(not test_bayes_nets, "skipping test_bayes_nets")
  def test_bayes_nets(self):
    print "\n TESTING INFERENCE ON CLOUDY/SPRINKLER\n"
    
    #niters, burnin = 1000, 100
    niters, burnin = 10, 10
  
    assume('cloudy', bernoulli(constant(0.5)))
    assume('sprinkler', ifelse(var('cloudy'), bernoulli(constant(0.1)), bernoulli(constant(0.5))))
    #d = test_prior(niters, burnin)
    #self.assertTrue(test_prior_bool(d, 'cloudy') < 0.1)
    #self.assertTrue(test_prior_bool(d, 'sprinkler') < 0.1)
    #print infer_many('cloudy', niters, burnin)
    #print 'Should be .5 False, .5 True'
    #print infer_many('sprinkler', niters, burnin)
    #print 'Should be .7 False, .3 True'
    
    noise_level = .01
    sprinkler_ob = observe(noisy(var('sprinkler'), noise_level), Value(True))
    #d = infer_many('cloudy', niters, burnin)
    #print d
    #self.assertTrue(  abs(d['cloudy'][False] / (niters + 0.0) - 5 / 6.0) < 0.1)
    #self.assertTrue(test_prior_bool(d, 'sprinkler') < 0.1)
    #print 'Should be .833 False, .166 True'
    #print infer_many('sprinkler', niters, burnin)
    #print 'Should be 0 False, 1 True'
    
    a = follow_prior(['cloudy', 'sprinkler'], 1000, 100, timer = False)
    #print [(x, count_up(a[x])) for x in a]
  
    forget(sprinkler_ob)
    #print infer_many('cloudy', niters, burnin)
    #print 'Should be .500 False, .500 True'
  
    #print "\n TESTING BEACH NET\n"
    
    #niters, burnin = 1000, 50
    niters, burnin = 10, 5
  
    reset()
    assume('sunny', bernoulli(constant(0.5)))
    assume('weekend', bernoulli(constant(0.285714)))
    #assume('beach', bernoulli(ifelse('weekend', ifelse('sunny', 0.9, 0.5), \
    #                                            ifelse('sunny', 0.3, 0.1))))

    #assume('beach', ifelse('weekend', bernoulli(ifelse('sunny', 0.9, 0.5)), \
    #                                  bernoulli(ifelse('sunny', 0.3, 0.1))))

    assume('beach', ifelse(var('weekend'), ifelse(var('sunny'), bernoulli(constant(0.9)), bernoulli(constant(0.5))), \
                                           ifelse(var('sunny'), bernoulli(constant(0.3)), bernoulli(constant(0.1)))))
    #  this mixes poorly sometimes because the inactive branch gets stuck

    #print test_prior(1000, 100)
    
    observe(noisy(var('weekend'), noise_level), Value(True))
    #print infer_many('sunny', niters, burnin)
    #print 'Should be .5 False, .5 True'
    
    observe(noisy(var('beach'), noise_level), Value(True))
    print infer_many('sunny', niters, burnin)
    print 'Should be .357142857 False, .642857143 True'

    #print "\n TESTING BURGLARY NET\n" # An example from AIMA
  
    #pB = 0.001
    #pE = 0.002
    #pAgBE = 0.95
    #pAgBnE = 0.94
    #pAgnBE = 0.29
    #pAgnBnE = 0.001
    #pJgA = 0.9
    #pJgnA = 0.05
    #pMgA = 0.7
    #pMgnA = 0.01
    #
    #pA = pB * pE * pAgBE + (1-pB) * pE * pAgnBE + pB * (1 - pE) * pAgBnE + (1-pB) * (1-pE) * pAgnBnE
    #
    #pJ = pA * pJgA + (1 - pA) * pJgnA
    #
    #pAgnB = (pE * pAgnBE + (1 - pE) * pAgnBnE) / (1 - pB)
    #pJgnB = pJgA * pAgnB + pJgnA * (1 - pAgnB) 
    #
    #pAgM = pMgA * pA / (pMgA * pA + pMgnA * (1 - pA))
    #pJgM = pAgM * pJgA + (1 - pAgM) * pJgnA
    #
    #pJnB = pJgnB * (1 - pB)

    print "\n TESTING MODIFIED BURGLARY NET\n" # An example from AIMA
    reset()
  
    #niters, burnin = 1000, 100
    niters, burnin = 10, 10
  
    pB = 0.1
    pE = 0.2
    pAgBE, pAgBnE, pAgnBE, pAgnBnE = 0.95, 0.94, 0.29, 0.10
    pJgA, pJgnA = 0.9, 0.5
    pMgA, pMgnA = 0.7, 0.1
    
    pA = pB * pE * pAgBE + (1-pB) * pE * pAgnBE + pB * (1 - pE) * pAgBnE + (1-pB) * (1-pE) * pAgnBnE
    
    pJ = pA * pJgA + (1 - pA) * pJgnA
    
    pAgnB = (pE * pAgnBE + (1 - pE) * pAgnBnE) / (1 - pB)
    pJgnB = pJgA * pAgnB + pJgnA * (1 - pAgnB) 
    
    pAgM = pMgA * pA / (pMgA * pA + pMgnA * (1 - pA))
    pJgM = pAgM * pJgA + (1 - pAgM) * pJgnA
    
    pJnB = pJgnB * (1 - pB)
    
    assume('burglary', bernoulli(constant(pB)))
    assume('earthquake', bernoulli(constant(pE)))
    assume('alarm', ifelse(var('burglary'), ifelse(var('earthquake'), bernoulli(constant(pAgBE)), bernoulli(constant(pAgBnE))), \
                                            ifelse(var('earthquake'), bernoulli(constant(pAgnBE)), bernoulli(constant(pAgnBnE)))))
  
    assume('johnCalls', ifelse(var('alarm'),  bernoulli(constant(pJgA)), bernoulli(constant(pJgnA))))
    assume('maryCalls', ifelse(var('alarm'),  bernoulli(constant(pMgA)), bernoulli(constant(pMgnA))))
    print test_prior(1000, 100, timer = False)
  
    print infer_many('alarm', niters, burnin)
    print 'Should be %f True' % pA
  
    mary_ob = observe(noisy(var('maryCalls'), noise_level), Value(True))
    print infer_many('johnCalls', niters, burnin)
    print 'Should be %f True' % pJgM
    forget(mary_ob)
  
    burglary_ob = observe(noisy(~var('burglary'), noise_level), Value(True))
    print infer_many('johnCalls', niters, burnin)
    print 'Should be %f True' % pJgnB
    forget(burglary_ob)
  
  
  @unittest.skipIf(not test_xor, "skipping test_xor")
  def test_xor(self):
    # needs like 500 to mix
    p = 0.6
    q = 0.4
    noise_level = .01
    assume('a', bernoulli(constant(p))) 
    assume('b', bernoulli(constant(q))) 
    assume('c', var('a') ^ var('b'))

    d = test_prior(1000, 100, timer = False)
    print d
    self.assertTrue(test_prior_bool(d, 'a') < 0.05)
    self.assertTrue(test_prior_bool(d, 'b') < 0.05)
    self.assertTrue(test_prior_bool(d, 'c') < 0.05)
  
    #xor_ob = observe(noisy('c', noise_level), Value(True)) 
    #print infer_many('a', 100, 500) 
    #print 'should be 0.69 true'
    # should be True : p(1-q)/(p(1-q)+(1-p)q), False : q(1-p)/(p(1-q) + q(1-p)) 
    # I believe this gets skewed because it has to pass through illegal states, and the noise values get rounded badly 
  
  @unittest.skipIf(not test_recursion, "skipping test_recursion")
  def test_recursion(self):
    
    factorial_expr = function('x', ifelse(var('x') == constant(0), constant(1), \
                var('x') * apply(var('factorial'), var('x') - constant(1)))) 
    assume('factorial', factorial_expr) 
    
    self.assertTrue(sample(apply(var('factorial'), constant(5))).val == 120)
    self.assertTrue(sample(apply(var('factorial'), constant(10))).val == 3628800)
  
  @unittest.skipIf(not test_mem, "skipping test_mem")
  def test_mem(self):
    fibonacci_expr = function('x', ifelse(var('x') <= constant(1), constant(1), \
                  apply(var('fibonacci'), var('x') - constant(1)) + apply(var('fibonacci'), var('x') - constant(2)) )) 
    assume('fibonacci', fibonacci_expr) 
    
    t1 = time()
    self.assertTrue(sample(apply(var('fibonacci'), constant(20))).val == 10946)
    t1 = time() - t1

    assume('bad_mem_fibonacci', mem(var('fibonacci'))) 
  
    t2 = time()
    self.assertTrue(sample(apply(var('bad_mem_fibonacci'), constant(20))).val == 10946)
    t2 = time() - t2

    t3 = time()
    self.assertTrue(sample(apply(var('bad_mem_fibonacci'), constant(20))).val == 10946)
    t3 = time() - t3

    mem_fibonacci_expr = function('x', ifelse(var('x') <= constant(1), constant(1), \
                  apply(var('mem_fibonacci'), var('x') - constant(1)) + apply(var('mem_fibonacci'), var('x') - constant(2)) )) 
    assume('mem_fibonacci', mem(mem_fibonacci_expr)) 
  
    t4 = time()
    self.assertTrue(sample(apply(var('mem_fibonacci'), constant(20))).val == 10946)
    t4 = time() - t4

    print t1, t2, t3, t4
    self.assertTrue(0.5 < (t1 / t2) < 2)
    self.assertTrue((t3 / t2) < .01)
    self.assertTrue((t3 / t4) < .1)
    self.assertTrue((t4 / t2) < .1)
  
  @unittest.skipIf(not test_geometric, "skipping test_geometric")
  def test_geometric(self):
    a, b = 3, 2
    timetodecay = 1
    bucketsize = .01
  
    niters, burnin = 1000, 100 
  
    assume('decay', beta(constant(a), constant(b)))
    assume('geometric', function('x', ifelse(bernoulli(var('decay')), var('x'), apply(var('geometric'), var('x') + constant(1)))))
    assume('timetodecay', apply(var('geometric'), constant(0)))

    d = test_prior(1000, 100, timer = False)
    print d
    #self.assertTrue(test_prior_L0(d, 'decay', 0, 1, .01) < .1)
    #self.assertTrue(test_prior_L0(d, 'timetodecay', 0, 100, 1) < .1)

    # hmm... random walk systematically decays faster
  
    observe(noisy(var('timetodecay') == constant(timetodecay), .001), Value(True))
    dist = infer_many('decay', niters, burnin)
    #print dist 
    #print 'pdf:', get_pdf(dist, 0, 1, .1)
    #print 'cdf:', get_cdf(dist, 0, 1, .1)
  
    plot_beta_cdf(a, b, bucketsize, name = 'graphs/prior.png')
    plot_cdf(dist, 0, 1, bucketsize, name = 'graphs/geometric%d.png' % burnin)
    plot_beta_cdf(a + 1, b + timetodecay, bucketsize, name = 'graphs/posterior.png')
  
    prior_cdf = get_beta_cdf(a, b, bucketsize)
    posterior_cdf = get_beta_cdf(a + 1, b+timetodecay, bucketsize)
    dist_cdf = get_cdf(dist, 0, 1, bucketsize)
  
    print "L0 distance from prior     = %0.3f" % L0distance(prior_cdf, dist_cdf)
  
    print "L0 distance from posterior = %0.3f" % L0distance(posterior_cdf, dist_cdf)   
  
    print "L1 distance from prior     = %0.3f" % L1distance(prior_cdf, dist_cdf)
  
    print "L1 distance from posterior = %0.3f" % L1distance(posterior_cdf, dist_cdf)   
  
  @unittest.skipIf(not test_DPmem, "skipping test_DPmem")
  def test_DPmem(self):
  
    def count_distinct(ls):
      d = Set()
      dd = Set()
      count = 0
      duplicates = 0
      for x in ls:
        if x not in d:
          d.add(x)
          count += 1
        else:
          if x not in dd:
            dd.add(x)
            duplicates += 1
      return duplicates 
  
    concentration = 10
    measure = function([], gaussian(0, 1))
  
    """DEFINITION OF DP"""
  
    assume('DP', \
           function(['concentration', 'basemeasure'], \
                    let([('sticks', mem(function('j', beta(1, 'concentration')))),
                         ('atoms',  mem(function('j', apply('basemeasure')))),
                         ('loop', \
                          function('j', \
                                   ifelse(bernoulli(apply('sticks', 'j')), \
                                          apply('atoms', 'j'), \
                                          apply('loop', var('j')+1)))) \
                        ], \
                        function([], apply('loop', 1))))) 
  
    print "TEST VERSION"
    assume('DPgaussian', apply('DP', [concentration, measure]))
    print 'DPGaussian = ', sample('DPgaussian')
    ls = [sample(apply('DPgaussian')) for i in xrange(10)]
    print ls
    print count_distinct(ls)
  
    """TESTING DP"""
    if simpletests:
      concentration = .1 # when close to 0, lots of repeat.  when close to infinity, many new sample 
      assume('DPgaussian', apply('DP', [concentration, function([], gaussian(0, 1))]))
      print [sample(apply('DPgaussian')) for i in xrange(10)]
  
      concentration = 10 # when close to 0, lots of repeat.  when close to infinity, many new sample 
      assume('DPgaussian', apply('DP', [concentration, function([], gaussian(0, 1))]))
      print [sample(apply('DPgaussian')) for i in xrange(10)]
  
    print " \n TESTING DPMem\n"
  
    """DEFINITION OF DPMEM"""
    # Only supports function with exactly one argument
    assume('DPmem', \
           function(['concentration', 'proc'], \
                    let([('restaurants', \
                          mem( function('args', apply('DP', ['concentration', function([], apply('proc', 'args'))]))))], \
                        function('args', apply('restaurants', 'args'))))) 
  
    """TESTING DPMEM"""
    concentration = 1 # when close to 0, just mem.  when close to infinity, sample 
    assume('DPmemflip', apply('DPmem', [concentration, function(['x'], gaussian(0, 1))]))
  
    print "\n TESTING GAUSSIAN MIXTURE MODEL\n"
    assume('expected-mean', gaussian(0, 5)) 
    assume('expected-variance', gamma(1, 2)) 
    assume('alpha', gamma(0.1, 10)) 
    assume('gen-cluster-mean', apply('DPmem', ['alpha', function(['x'], gaussian('expected-mean', 'expected-variance'))]))
    assume('get-datapoint', mem(function(['id'], gaussian(apply(apply('gen-cluster-mean', 222)), 0.1))))
    assume('noise-variance', gamma(0.01, 1))
  
  #  points = {} 
  #  for i in xrange(100):
  #    print sample(apply('get-datapoint', i))
  #  for i in xrange(1000):
  #    val = sample(apply('get-datapoint', i))
  #    if val in points:
  #      points[val] += 1
  #    else:
  #      points[val] = 1
  #  plot_pdf(points, -50, 50, 0.1, name = 'graphs/mixturesample.png')
  
    #assume('x', apply(var('get-datapoint'), constant(0)))
    #observe(gaussian('x', let([('x', gaussian(constant(0), var('outer-noise')))], var('x') * var('x'))), Value(2.3))
    #observe(gaussian(apply(var('get-datapoint'), constant(1)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(2.2))
    #observe(gaussian(apply(var('get-datapoint'), constant(2)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(1.9))
    #observe(gaussian(apply(var('get-datapoint'), constant(3)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(2.0))
    #observe(gaussian(apply(var('get-datapoint'), constant(4)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(2.1))

    observe(gaussian(apply(var('get-datapoint'), constant(0)), var('noise-variance')), Value(2.3))
    observe(gaussian(apply(var('get-datapoint'), constant(1)), var('noise-variance')), Value(2.2))
    observe(gaussian(apply(var('get-datapoint'), constant(2)), var('noise-variance')), Value(1.9))
    observe(gaussian(apply(var('get-datapoint'), constant(3)), var('noise-variance')), Value(2.0))
    observe(gaussian(apply(var('get-datapoint'), constant(4)), var('noise-variance')), Value(2.1))
  
    #niters, burnin = 100, 100
  
    a = infer_many(apply('get-datapoint', 0), 10, 1000)
    print sample(apply('get-datapoint', 0))
    print sample(apply('get-datapoint', 0))
    print sample(apply('get-datapoint', 0))
    print a
    #print format(get_pdf(a, -4, 4, .5), '%0.2f') 
  
    #print 'running', niters, 'times,', burnin, 'burnin'
  
    #t = time()
    #a = infer_many('expected-mean', niters, burnin)
    #print format(get_pdf(a, -4, 4, .5), '%0.2f') 
    #print 'time taken', time() - t
  
  @unittest.skipIf(not test_easy_mixture, "skipping test_easy_mixture")
  def test_easy_mixture(self):
  
    x = []
    y = []
  
    for i in range(0, 500, 100):
      reset()
      assume('get-cluster-mean', gaussian(0, 10))
      assume('get-cluster-variance', gamma(1, 10))
      assume('get-cluster-model', function([], gaussian('get-cluster-mean', 'get-cluster-variance')))
      assume('get-datapoint-2', mem(function('id', apply('get-cluster-model'))))
      assume('get-datapoint', mem(function('id', gaussian(apply('get-cluster-model'), 0.1))))
  
      points = [2.2, 2.0, 1.5, 2.1, 1.8, 1.9]
      print "points: " + str(points)
      for (idx, p) in enumerate(points):
        observe(gaussian(apply('get-datapoint-2', idx), 0.1), Value(p))
  
      #assume('x', apply(var('get-datapoint'), constant(0)))
      #observe(gaussian(var('x'), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(2.3))
      #observe(gaussian(apply(var('get-datapoint'), constant(1)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(2.2))
      #observe(gaussian(apply(var('get-datapoint'), constant(2)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(1.9))
      #observe(gaussian(apply(var('get-datapoint'), constant(3)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(2.0))
      #observe(gaussian(apply(var('get-datapoint'), constant(4)), let([('y', gaussian(constant(0), var('outer-noise')))], var('y') * var('y'))), Value(2.1))
  
      avg_logpdf = 0
      num_repeats = 10
      for j in range(0, num_repeats):
        # start at prior, move i steps towards posterior
        a = infer_many('get-cluster-mean', 1, i)
  
        # read out inferred mean and sig of gaussian
        avg = sample('get-cluster-mean').val
        sig = sample('get-cluster-variance').val
  
        print "  mean: " + str(avg) + " +- " + str(sig)
  
        logpdf = 0
        for point in points:  
          logpdf += -((point - avg)/(sig + 0.0))**2
        logpdf /= float(len(points))
        print "  logpdf for trial " + str(j) + " iters " + str(i) + " : " + str(logpdf)
  
        avg_logpdf += logpdf
  
      print "total logpdf: " + str(avg_logpdf)
      avg_logpdf /= float(num_repeats)
      print "avg_logpdf: " + str(avg_logpdf)
  
      y.append(avg_logpdf) # log pdf at point
      x.append(i)
    plot(x, y, name = 'graphs/mixture1component.png')
    #print [sample('x') for i in xrange(10)]
  
    reset()
  
    print " \n TESTING 2 COMPONENT MIXTURE\n"
  
    assume('cluster-crp', function([], uniform(2)))
    assume('get-cluster-mean', function('cluster', gaussian(0, 10)))
    assume('get-cluster-variance', function('cluster', gamma(1, 10)))
    assume('get-cluster', function('id' , apply('cluster-crp')))
    assume('get-cluster-model', mem(function('cluster', function([], gaussian(apply('get-cluster-mean', 'cluster'), apply('get-cluster-variance', 'cluster'))))))
    assume('get-datapoint', mem(function('id', gaussian(apply(apply('get-cluster-model', apply('get-cluster', 'id'))), 0.1))))
  
    assume('x', apply('get-datapoint', 0))
    #observe(gaussian('x', let([('y', gaussian(0, .1))], var('y') * var('y'))), Value(-2.3))
    #observe(gaussian(apply('get-datapoint', 1), let([('y', gaussian(0, .1))], var('y') * var('y'))), Value(-2.2))
    #observe(gaussian(apply('get-datapoint', 2), let([('y', gaussian(0, .1))], var('y') * var('y'))), Value(-1.9))
    #observe(gaussian(apply('get-datapoint', 3), let([('y', gaussian(0, .1))], var('y') * var('y'))), Value(-2.0))
    #observe(gaussian(apply('get-datapoint', 4), let([('y', gaussian(0, .1))], var('y') * var('y'))), Value(-2.1))
  
    #a = infer_many('x', 10, 1000)
    #print a
    #print [sample('x') for i in xrange(10)]

  @unittest.skipIf(True, "Always skip")
  def test():
    print " \n TESTING BLAH\n"
    
    #print "description"
    #expr = beta_bernoulli_1()
    #print [sample(apply(coin_1)) for i in xrange(10)]
    
    print "description"
    assume('f', mem(let(('x', CRP(1)), function(['id'], apply('x')))))
    #for i in range(20):
    #  print sample(apply('f', i))
    assume('x', apply('f', 0))
    print test_prior(1000, 100)
  
    observe(noisy(apply('f',0) < 2222222222, 0.001), Value(True))
    a = infer_many(apply('f',0), 10, 1000)
    print a
    print sample(apply('f', 0))
    print sample(apply('f', 0))
    print sample(apply('f', 0))
    print sample(apply('f', 0))
    #print [sample('x') for i in xrange(10)]

def run_HMM(t, s, niters = 1000, burnin = 100, countup = True):
    reset()
    random.seed(s)
    n = 5
    assume('dirichlet', dirichlet_no_args_XRP([1]*n))
    assume('get-column', mem(function('i', apply('dirichlet'))))
    assume('get-next-state', function('i',
                             let([('loop', \
                                  function(['v', 'j'], \
                                           let([('w', apply(apply('get-column', 'i'), 'j'))],
                                            ifelse(var('v') < 'w', 'j', apply('loop', [var('v') -'w', var('j') + 1]))))) \
                                 ], \
                                 apply('loop', [uniform(), 0]))))
    assume('state', mem(function('i',
                                 ifelse(var('i') == 0, 0, apply('get-next-state', apply('state', var('i') - 1))))))
  
    assume('start-state', apply('state', 0))
    assume('last-state', apply('state', t))
    a = test_prior(niters, burnin, countup)
    return a

def run_topic_model(docsize, s, niters = 1000, burnin = 100, countup = True):
    reset()
    random.seed(s)
    ntopics = 5
    nwords = 20

    assume('topics-dirichlet', dirichlet_no_args_XRP([1]*ntopics))
    assume('words-dirichlet', dirichlet_no_args_XRP([1]*nwords))

    assume('get-topic-dist', apply('topics-dirichlet'))
    assume('get-topic-words-dist', mem(function('i', apply('words-dirichlet'))))
    assume('sample-dirichlet', function('prob_array',
                               let([('loop', 
                                    function(['v', 'i'], 
                                             let([('w', apply('prob_array', 'i'))], 
                                              ifelse(var('v') < 'w', 'i', apply('loop', [var('v') -'w', var('i') + 1])))))
                                   ], 
                                   apply('loop', [uniform(), 0]))))
    assume('get-topic', mem(function('i', apply('sample-dirichlet', 'get-topic-dist'))))
    assume('get-word', mem(function('i', apply('sample-dirichlet', apply('get-topic-words-dist', apply('get-topic', 'i'))))))

    for i in range(docsize):
      assume('get-word' + str(i), apply('get-word', i)) 

    a = test_prior(niters, burnin, countup)
    return a

def run_mixture(n, s, niters = 1000, burnin = 100, countup = True):
    reset()
    random.seed(s)

    assume('alpha', gamma(0.1, 20))
    assume('cluster-crp', CRP('alpha'))
    assume('get-cluster-mean', mem(function('cluster', gaussian(0, 10))))
    assume('get-cluster-variance', mem(function('cluster', gamma(0.1, 100))))
    assume('get-cluster', mem(function('id' , apply('cluster-crp'))))
    assume('get-cluster-model', mem(function('cluster', function([], gaussian(apply('get-cluster-mean', 'cluster'), apply('get-cluster-variance', 'cluster'))))))
    assume('get-datapoint', mem(function('id', gaussian(apply(apply('get-cluster-model', apply('get-cluster', 'id'))), 0.1))))

    for i in range(n):
      assume('point' + str(i), apply('get-datapoint', i))
    a = test_prior(niters, burnin, countup)
    return a

def run_mixture_uncollapsed(n, s):
    random.seed(s)

    """DEFINITION OF DP"""
    assume('DP', \
           function(['concentration', 'basemeasure'], \
                    let([('sticks', mem(function('j', beta(1, 'concentration')))),
                         ('atoms',  mem(function('j', apply('basemeasure')))),
                         ('loop', \
                          function('j', \
                                   ifelse(bernoulli(apply('sticks', 'j')), \
                                          apply('atoms', 'j'), \
                                          apply('loop', var('j')+1)))) \
                        ], \
                        function([], apply('loop', 1))))) 

    """DEFINITION OF ONE ARGUMENT DPMEM"""
    assume('DPmem', \
           function(['concentration', 'proc'], \
                    let([('restaurants', \
                          mem( function('args', apply('DP', ['concentration', function([], apply('proc', 'args'))]))))], \
                        function('args', apply('restaurants', 'args'))))) 

    print "\n TESTING GAUSSIAN MIXTURE MODEL\n"
    assume('expected-mean', gaussian(0, 5)) 
    assume('expected-variance', gamma(1, 2)) 
    assume('alpha', gamma(0.1, 10)) 
    assume('gen-cluster-mean', apply('DPmem', ['alpha', function(['x'], gaussian('expected-mean', 'expected-variance'))]))
    assume('get-datapoint', mem(function(['id'], gaussian(apply(apply('gen-cluster-mean', 222)), 0.1))))
    assume('noise-variance', gamma(0.01, 1))

    for i in range(n):
      assume('point' + str(i), apply('get-datapoint', i))
    a = infer_many(apply('get-datapoint', 0), 10, 1000)
    return a

def run_bayes_net(k, s, niters = 1000, burnin = 100, countup = True):
    reset()
    random.seed(s)
    n = 50

    for i in xrange(n):
      assume('disease' + str(i), bernoulli(constant(0.2)))
    for j in xrange(n):
      causes = ['disease' + str(random.randint(0,n-1)) for i in xrange(k)]
      symptom_expression = bernoulli(ifelse(disjunction(causes), .8, .2))
      assume('symptom' + str(j), symptom_expression)

    a = test_prior(niters, burnin, countup)
    return a

if __name__ == '__main__':
  t = time()
  running_main = True
  if not running_main:
    a = run_topic_model(5, 222222, 100)
    #a = run_HMM(5, 222222)
    #a = run_mixture(15, 222222)
    #a = run_bayes_net(20, 222222)
    sampletimes = a[0]['TIME']
    print average(sampletimes)
    print standard_deviation(sampletimes)
    
    followtimes = a[1]['TIME']
    print average(followtimes)
    print standard_deviation(followtimes)
    print time() - t
  else:
    unittest.main()
