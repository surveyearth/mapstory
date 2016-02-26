from haystack import signal_processor

class HaystackBatchFlushMiddleware(object):
    """
    for use with our BatchingSignalProcessor

    this should be placed *at the top* of MIDDLEWARE_CLASSES
    (so that it runs last)
    """
    def process_response(self, request, response):
        try:
            signal_processor.flush_changes()
        except AttributeError:
            # (in case we're not using our expected signal_processor)
            pass
        return response
