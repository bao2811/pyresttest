import math
import json
import pycurl
import sys

from . import tests
from .tests import Test
from . import parsing
from .parsing import *

# Python 2/3 switches
if sys.version_info[0] > 2:
    from past.builtins import basestring

# Python 3 compatibility shims
from . import six
from .six import binary_type
from .six import text_type

"""
Encapsulates logic related to benchmarking
- Parameters and fields for benchmarks
- Benchmark object that extends tests.Test object with additional fields
- Templating/Caching logic specific to benchmarks
"""


# Curl metrics for benchmarking, key is name in config file, value is pycurl variable
# Taken from pycurl docs, this is libcurl variable minus the CURLINFO prefix
# Descriptions of the timing variables are taken from libcurl docs:
#   http://curl.haxx.se/libcurl/c/curl_easy_getinfo.html

METRICS = {
    # Timing info, precisely in order from start to finish
    # The time it took from the start until the name resolving was completed.
    'namelookup_time': pycurl.NAMELOOKUP_TIME,

    # The time it took from the start until the connect to the remote host (or
    # proxy) was completed.
    'connect_time': pycurl.CONNECT_TIME,

    # The time it took from the start until the SSL connect/handshake with the
    # remote host was completed.
    'appconnect_time': pycurl.APPCONNECT_TIME,

    # The time it took from the start until the file transfer is just about to begin.
    # This includes all pre-transfer commands and negotiations that are
    # specific to the particular protocol(s) involved.
    'pretransfer_time': pycurl.PRETRANSFER_TIME,

    # The time it took from the start until the first byte is received by
    # libcurl.
    'starttransfer_time': pycurl.STARTTRANSFER_TIME,

    # The time it took for all redirection steps include name lookup, connect, pretransfer and transfer
    # before final transaction was started. So, this is zero if no redirection
    # took place.
    'redirect_time': pycurl.REDIRECT_TIME,

    # Total time of the previous request.
    'total_time': pycurl.TOTAL_TIME,


    # Transfer sizes and speeds
    'size_download': pycurl.SIZE_DOWNLOAD,
    'size_upload': pycurl.SIZE_UPLOAD,
    'request_size': pycurl.REQUEST_SIZE,
    'speed_download': pycurl.SPEED_DOWNLOAD,
    'speed_upload': pycurl.SPEED_UPLOAD,

    # Connection counts
    'redirect_count': pycurl.REDIRECT_COUNT,
    'num_connects': pycurl.NUM_CONNECTS
}

# Map statistical aggregate to the function to use to perform the
# aggregation on an array
AGGREGATES = {
    'mean_arithmetic':  # AKA the average, good for many things
    lambda x: float(sum(x)) / float(len(x)),
    'mean':  # Alias for arithmetic mean
    lambda x: float(sum(x)) / float(len(x)),
    'mean_harmonic':  # Harmonic mean, better predicts average of rates: http://en.wikipedia.org/wiki/Harmonic_mean
    lambda x: 1.0 / (sum([1.0 / float(y) for y in x]) / float(len(x))),
    'median': lambda x: median(x),
    # Backwards-compatible percentile names used historically (p50/p95/p99)
    'p50': lambda x: percentile(x, 50),
    'p95': lambda x: percentile(x, 95),
    'p99': lambda x: percentile(x, 99),
    'std_deviation': lambda x: std_deviation(x),
    'sum': lambda x: sum(x),
    'total': lambda x: sum(x)
}

OUTPUT_FORMATS = [u'csv', u'json']


def median(array):
    """ Get the median of an array """
    mysorted = [x for x in array]
    mysorted.sort()
    middle = int(len(mysorted) / 2)  # Gets the middle element, if present
    if len(mysorted) % 2 == 0:  # Even, so need to average together the middle two values
        return float((mysorted[middle] + mysorted[middle - 1])) / 2
    else:
        return mysorted[middle]


def percentile(array, p):
    """Return the p-th percentile (linear interpolation) of array"""
    if not array:
        return None
    s = sorted(array)
    k = (len(s) - 1) * (p / 100.0)
    f = int(math.floor(k))
    c = int(math.ceil(k))
    if f == c:
        return float(s[int(k)])
    d0 = s[f] * (c - k)
    d1 = s[c] * (k - f)
    return float(d0 + d1)


def std_deviation(array):
    """ Compute the standard deviation of an array of numbers """
    if not array or len(array) == 1:
        return 0

    average = AGGREGATES['mean_arithmetic'](array)
    variance = map(lambda x: (x - average)**2, array)
    try:
        len(variance)
    except TypeError:  # Python 3.3 workaround until can use the statistics module from 3.4
        variance = list(variance)
    stdev = AGGREGATES['mean_arithmetic'](variance)
    return math.sqrt(stdev)


class Benchmark(Test):
    """ Extends test with configuration for benchmarking
        warmup_runs and benchmark_runs behave like you'd expect

        Metrics are a bit tricky:
            - Key is metric name from METRICS
            - Value is either a single value or a list:
                - list contains aggregagate name from AGGREGATES
                - value of 'all' returns everything
    """
    warmup_runs = 10  # Times call is executed to warm up
    benchmark_runs = 100  # Times call is executed to generate benchmark results
    output_format = u'csv'
    output_file = None
    # Allow reusing connections by default (keep-alive). Set to False to forbid reuse.
    allow_connection_reuse = True
    # Performance mode: 'sync' (default) or 'async'
    mode = 'sync'

    # Metrics to gather, both raw and aggregated
    metrics = set()

    raw_metrics = set()  # Metrics that do not have any aggregation performed
    # Metrics where an aggregate is computed, maps key(metric name) ->
    # list(aggregates to use)
    aggregated_metrics = dict()

    def ninja_copy(self):
        """ Optimization: limited, fast copy of benchmark, overrides Test parent method """
        output = Benchmark()
        myvars = vars(self)
        output.__dict__ = myvars.copy()
        return output

    def add_metric(self, metric_name, aggregate=None):
        """ Add a metric-aggregate pair to the benchmark, where metric is a number to measure from curl, and aggregate is an aggregation function
            (See METRICS and AGGREGATES)
            If aggregate is not defined (False,empty, or None), then the raw number is reported
            Returns self, for fluent-syle construction of config """

        clean_metric = metric_name.lower().strip()

        if clean_metric.lower() not in METRICS:
            raise Exception("Metric named: " + metric_name +
                            " is not a valid benchmark metric.")
        self.metrics.add(clean_metric)

        if not aggregate:
            self.raw_metrics.add(clean_metric)
        elif aggregate.lower().strip() in AGGREGATES:
            # Add aggregate to this metric
            clean_aggregate = aggregate.lower().strip()
            current_aggregates = self.aggregated_metrics.get(
                clean_metric, list())
            current_aggregates.append(clean_aggregate)
            self.aggregated_metrics[clean_metric] = current_aggregates
        else:
            raise Exception("Aggregate function " + aggregate +
                            " is not a legal aggregate function name")

        return self

    def __init__(self):
        self.metrics = set()
        self.raw_metrics = set()
        self.aggregated_metrics = dict()
        super(Benchmark, self).__init__()

    def __str__(self):
        return json.dumps(self, default=safe_to_json)


def realize_partial(self, context=None):
    """ Attempt to template out what is possible for this benchmark """
    if not self.is_dynamic():
        return self
    if self.is_context_modifier():
        # Enhanceme - once extract is done, check if variables already bound,
        # in that case template out
        return self
    else:
        copyout = copy.cop

    pass


def configure_curl(self, timeout=tests.DEFAULT_TIMEOUT, context=None, curl_handle=None):
    curl = super().configure_curl(self, timeout=timeout,
                                  context=context, curl_handle=curl_handle)
    # Respect benchmark's preference for connection reuse. By default we allow
    # reusing connections which enables keep-alive and avoids TCP/TLS handshake
    # per request. To simulate separate users/clients set Benchmark.allow_connection_reuse=False
    try:
        if getattr(self, 'allow_connection_reuse', True):
            # allow reuse: ensure FORBID_REUSE is not set (default behavior)
            pass
        else:
            # forbid reuse: prevent keep-alive
            curl.setopt(pycurl.FORBID_REUSE, 1)
    except Exception:
        # If pycurl doesn't support an option or any other error occurs,
        # fall back to default behavior (allow reuse)
        pass
    return curl


def parse_benchmark(base_url, node):
    """ Try building a benchmark configuration from deserialized configuration root node """
    node = lowercase_keys(flatten_dictionaries(node))  # Make it usable

    benchmark = Benchmark()

    # Read & set basic test parameters
    benchmark = Test.parse_test(base_url, node, benchmark)

    # Complex parsing because of list/dictionary/singleton legal cases
    for key, value in node.items():
        if key == u'warmup_runs':
            benchmark.warmup_runs = int(value)
        elif key == u'benchmark_runs':
            benchmark.benchmark_runs = int(value)
        elif key == u'repeat' or key == u'repeat_runs':
            # alias for benchmark_runs
            benchmark.benchmark_runs = int(value)
        elif key == u'workers':
            benchmark.workers = int(value)
        elif key == u'concurrency' or key == u'max_concurrency':
            if value is not None:
                benchmark.concurrency = int(value)
        elif key == u'timeout':
            # timeout in seconds for each request
            if value is not None:
                benchmark.timeout = float(value)
        elif key == u'retry':
            # retry can be a dict with keys: max_retries, backoff_base, backoff_max, retry_statuses
            if isinstance(value, dict):
                from .retry import RetryConfig
                max_retries = int(value.get('max_retries') or 3)
                backoff_base = float(value.get('backoff_base') or 0.5)
                backoff_max = float(value.get('backoff_max') or 30.0)
                retry_statuses = value.get('retry_statuses', None)
                # ensure list of ints
                if retry_statuses is not None:
                    retry_statuses = [int(x) for x in retry_statuses]
                benchmark.retry_config = RetryConfig(max_retries=max_retries, backoff_base=backoff_base, backoff_max=backoff_max, retry_statuses=retry_statuses)
            else:
                raise TypeError('retry must be a mapping of retry settings')
        elif key == u'rps_mode':
            # allow configuring how RPS is computed: 'wall' or 'response'
            benchmark.rps_mode = str(value).lower()
        elif key == u'mode':
            mode = value.lower().strip()
            if mode in ('sync', 'async'):
                benchmark.mode = mode
            else:
                raise ValueError('Invalid benchmark mode: ' + mode + '. Must be "sync" or "async".')
        elif key == u'output_format':
            format = value.lower()
            if format in OUTPUT_FORMATS:
                benchmark.output_format = format
            else:
                raise ValueError('Invalid benchmark output format: ' + format)
        elif key == u'output_file':
            if not isinstance(value, basestring):
                raise ValueError("Invalid output file format")
            benchmark.output_file = value
        elif key == u'metrics':
            if isinstance(value, basestring):
                # Single value
                benchmark.add_metric(tests.coerce_to_string(value))
            # FIXME refactor the parsing of metrics here, lots of duplicated logic
            elif isinstance(value, list) or isinstance(value, set):
                # List of single values or list of {metric:aggregate, ...}
                for metric in value:
                    if isinstance(metric, dict):
                        for metricname, aggregate in metric.items():
                            # Backwards-compat: support {'percentiles':[50,95]} or {'p50':'p50'} style
                            if not isinstance(metricname, basestring):
                                raise TypeError(
                                    "Invalid metric input: non-string metric name")
                            # percentiles list
                            if metricname.lower() in (u'percentiles', u'percentile') and isinstance(aggregate, (list, tuple)):
                                for p in aggregate:
                                    try:
                                        pn = int(p)
                                    except Exception:
                                        raise TypeError("Invalid percentile value: %r" % (p,))
                                    benchmark.add_metric(tests.coerce_to_string('total_time'), tests.coerce_to_string('p%d' % pn))
                                continue
                            # p50 / p95 style where metricname indicates percentile
                            import re
                            if re.match(r'^p\d+$', metricname, flags=re.IGNORECASE):
                                # use total_time as the metric and metricname as aggregate
                                benchmark.add_metric(tests.coerce_to_string('total_time'), tests.coerce_to_string(metricname))
                                continue
                            if not isinstance(aggregate, basestring):
                                raise TypeError(
                                    "Invalid aggregate input: non-string aggregate name")
                            # TODO unicode-safe this
                            benchmark.add_metric(tests.coerce_to_string(metricname),
                                tests.coerce_to_string(aggregate))

                    elif isinstance(metric, basestring):
                        benchmark.add_metric(tests.coerce_to_string(metric))
            elif isinstance(value, dict):
                # Dictionary of metric-aggregate pairs
                for metricname, aggregate in value.items():
                    if not isinstance(metricname, basestring):
                        raise TypeError(
                            "Invalid metric input: non-string metric name")
                    # percentiles list
                    if metricname.lower() in (u'percentiles', u'percentile') and isinstance(aggregate, (list, tuple)):
                        for p in aggregate:
                            try:
                                pn = int(p)
                            except Exception:
                                raise TypeError("Invalid percentile value: %r" % (p,))
                            benchmark.add_metric(tests.coerce_to_string('total_time'), tests.coerce_to_string('p%d' % pn))
                        continue
                    # p50 / p95 style where metricname indicates percentile
                    import re
                    if re.match(r'^p\d+$', metricname, flags=re.IGNORECASE):
                        benchmark.add_metric(tests.coerce_to_string('total_time'), tests.coerce_to_string(metricname))
                        continue
                    if not isinstance(aggregate, basestring):
                        raise TypeError(
                            "Invalid aggregate input: non-string aggregate name")
                    benchmark.add_metric(tests.coerce_to_string(metricname),
                        tests.coerce_to_string(aggregate))
            else:
                raise TypeError(
                    "Invalid benchmark metric datatype: " + str(value))

    return benchmark
