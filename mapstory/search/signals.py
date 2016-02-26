from __future__ import absolute_import, division, print_function, unicode_literals
from django.db import models
from haystack.exceptions import NotHandled
from polymorphic import PolymorphicModel
from collections import OrderedDict


class BaseSignalProcessor(object):
    """
    A convenient way to attach Haystack to Django's signals & cause things to
    index.
    By default, does nothing with signals but provides underlying functionality.
    """

    _change_list = OrderedDict()

    def __init__(self, connections, connection_router):
        self.connections = connections
        self.connection_router = connection_router
        self.setup()

    def _add_change(self, method, sender, instance, using):
        key = (sender, instance.pk, using)
        if key in self._change_list:
            del self._change_list[key]
        self._change_list[key] = (method, instance, using)

    def setup(self):
        """
        A hook for setting up anything necessary for
        ``handle_save/handle_delete`` to be executed.
        Default behavior is to do nothing (``pass``).
        """
        # Do nothing.
        pass

    def teardown(self):
        """
        A hook for tearing down anything necessary for
        ``handle_save/handle_delete`` to no longer be executed.
        Default behavior is to do nothing (``pass``).
        """
        # Do nothing.
        pass

    def handle_save(self, sender, instance, **kwargs):
        """
        Given an individual model instance, determine which backends the
        update should be sent to & update the object on those backends.
        """

        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                # if this signal receives a polymorphic model, return the real class/instance
                if isinstance(instance, PolymorphicModel):
                    sender = instance.get_real_instance_class()
                    instance = instance.get_real_instance()

                index = self.connections[using].get_unified_index().get_index(sender)
                method = index.update_object
                self._add_change(method, sender, instance, using)
                #index.update_object(instance, using=using)

            except NotHandled:
                # TODO: Maybe log it or let the exception bubble?
                pass

    def handle_delete(self, sender, instance, **kwargs):
        """
        Given an individual model instance, determine which backends the
        delete should be sent to & delete the object on those backends.
        """
        using_backends = self.connection_router.for_write(instance=instance)

        for using in using_backends:
            try:
                index = self.connections[using].get_unified_index().get_index(sender)
                method = index.remove_object
                self._add_change(method, sender, instance, using)
                #index.remove_object(instance, using=using)
            except NotHandled:
                # TODO: Maybe log it or let the exception bubble?
                pass

    def flush_changes(self):
        while True:
            try:
                (sender, pk, using), (method, instance, using) = self._change_list.popitem(last=False)
            except KeyError:
                break
            else:
                method(instance, using)

class RealtimeSignalProcessor(BaseSignalProcessor):
    """
    Allows for observing when saves/deletes fire & automatically updates the
    search engine appropriately.
    """
    def setup(self):
        # Naive (listen to all model saves).
        models.signals.post_save.connect(self.handle_save)
        models.signals.post_delete.connect(self.handle_delete)
        # Efficient would be going through all backends & collecting all models
        # being used, then hooking up signals only for those.

    def teardown(self):
        # Naive (listen to all model saves).
        models.signals.post_save.disconnect(self.handle_save)
        models.signals.post_delete.disconnect(self.handle_delete)
        # Efficient would be going through all backends & collecting all models
        # being used, then disconnecting signals only for those.

