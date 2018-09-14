# Facedancer.py
#
# Contains the core methods for working with a facedancer, inclduing methods
# necessary for autodetection.
# and GoodFETMonitorApp.

import os
import time
import logging
from .errors import *
from facedancer.utils.ulogger import get_logger
from kitty.remote.rpc import RpcClient
from facedancer.fuzz.helpers import StageLogger, set_stage_logger

def FacedancerUSBApp(loglevel=0, quirks=None):
    """
    Convenience function that automatically creates a FacedancerApp
    based on the BOARD environment variable and some crude internal
    automagic.

    loglevel: Sets the verbosity level of the relevant app. Increasing
        this from zero yields progressively more output.
    """
    return FacedancerApp.autodetect(loglevel, quirks)


class FacedancerApp(object):
    app_name = "override this"
    name = "FacedancerApp"
    app_num = 0x00
    log_level = 0
    fuzzer=None
    count = 0

    @classmethod
    def set_log_level(self,loglevel):
        self.log_level=loglevel
        return get_logger(loglevel)

    @classmethod
    def get_log_level(self):
        return self.log_level

    def get_mutation(self, stage, data=None):
        if self.fuzzer:
            data = {} if data is None else data
            return self.fuzzer.get_mutation(stage=stage, data=data)
        return None


    @classmethod
    def usb_function_supported(self, reason=None):
        '''
        Callback from a USB device, notifying that the current USB device
        is supported by the host.

        :param reason: reason why we decided it is supported (default: None)
        '''
        self.current_usb_function_supported = True

    @classmethod
    def is_connected(self):
        return self.connected_device is not None

    @classmethod
    def autodetect(cls, loglevel=0, quirks=None):
        """
        Convenience function that automatically creates the apporpriate
        sublass based on the BOARD environment variable and some crude internal
        automagic.

        loglevel: Sets the verbosity level of the relevant app. Increasing
            this from zero yields progressively more output.
        """

        if 'BACKEND' in os.environ:
            backend_name = os.environ['BACKEND'].lower()
        else:
            backend_name = None

        # Iterate over each subclass of FacedancerApp until we find one
        # that seems appropriate.
        subclass = cls._find_appropriate_subclass(backend_name)

        if subclass:
            if loglevel > 0:
                print("Using {} backend.".format(subclass.app_name))

            return subclass(loglevel=loglevel, quirks=quirks)
        else:
            raise DeviceNotFoundError()


    @classmethod
    def _find_appropriate_subclass(cls, backend_name):

        # Recursive case: if we have any subnodes, see if they are
        # feed them to this function.
        for subclass in cls.__subclasses__():

            # Check to see if the subnode has any appropriate children.
            appropriate_class = subclass._find_appropriate_subclass(backend_name)

            # If it does, that's our answer!
            if appropriate_class:
                return appropriate_class

        # Base case: check the current node.
        if cls.appropriate_for_environment(backend_name):
            return cls
        else:
            return None

    @classmethod
    def appropriate_for_environment(cls, backend_name=None):
        """
        Returns true if the current class is likely to be the appropriate
        class to connect to a facedancer given the board_name and other
        environmental factors.

        board: The name of the backend, as typically retreived from the BACKEND
            environment variable, or None to try figuring things out based
            on other environmental factors.
        """
        return False

    # Fuzzer start
    def get_fuzzer(self,fhost,fport):
        fuzzer = RpcClient(host=fhost,port=int(fport))
        fuzzer.start()
        return fuzzer

    def send_heartbeat(self):
        heartbeat_file = 'heartbeat'
        if os.path.isdir(os.path.dirname(heartbeat_file)):
            with open(heartbeat_file, 'a'):
                os.utime(heartbeat_file, None)

    def check_connection_commands(self):
        '''
        :return: whether performed reconnection
        '''
        if self._should_disconnect():
            self.phy.disconnect()
            self._clear_disconnect_trigger()
            # wait for reconnection request; no point in returning to service_irqs loop while not connected!
            while not self._should_reconnect():
                self._clear_disconnect_trigger()  # be robust to additional disconnect requests
                time.sleep(0.1)
        # now that we received a reconnect request, flow into the handling of it...
        # be robust to reconnection requests, whether received after a disconnect request, or standalone
        # (not sure this is right, might be better to *not* be robust in the face of possible misuse?)
        if self._should_reconnect():
            self.phy.connect(self.dev)
            self._clear_reconnect_trigger()
            return True
        return False

    def _should_reconnect(self):
        if self.fuzzer:
            if os.path.isfile('trigger_reconnect'):
                return True
        return False

    def _clear_reconnect_trigger(self):
        trigger = 'trigger_reconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    def _should_disconnect(self):
        if self.fuzzer:
            if os.path.isfile('trigger_disconnect'):
                return True
        return False

    def _clear_disconnect_trigger(self):
        trigger = 'trigger_disconnect'
        if os.path.isfile(trigger):
            os.remove(trigger)

    # Fuzzer end
    
    # Stages start
    
    
    def setstage(self, stage_file_name):
        self.stage=True
        self.start_time = time.time()
        stage_logger = StageLogger(stage_file_name)
        stage_logger.start()
        set_stage_logger(stage_logger)

    
    def should_stop_phy(self):
        if self.fuzzer:
            self.count = (self.count + 1) % 50
            self.check_connection_commands()
            if self.count == 0:
                self.send_heartbeat()
            return False
        elif self.stage:
            stop_phy = False
            passed = int(time.time() - self.start_time)
            if passed > 5:
                self.logger.info('have been waiting long enough (over %d secs.), disconnect' % (passed))
                stop_phy = True
            return stop_phy
        else:
            return False
            
    # Stages end
          
    def __init__(self, device, loglevel=0):
        self.device = device
        self.loglevel = loglevel
        self.logger = logging.getLogger('facedancer')
        self.init_commands()

        if self.loglevel > 0:
            print(self.app_name, "initialized")

    def init_commands(self):
        pass

    def enable(self):
        pass

    def verbose(self, msg, *args, **kwargs):
        self.logger.verbose('[%s] %s' % (self.name, msg), *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self.logger.debug('[%s] %s' % (self.name, msg), *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self.logger.info('[%s] %s' % (self.name, msg), *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self.logger.warning('[%s] %s' % (self.name, msg), *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self.logger.error('[%s] %s' % (self.name, msg), *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        self.logger.critical('[%s] %s' % (self.name, msg), *args, **kwargs)

    def always(self, msg, *args, **kwargs):
        self.logger.always('[%s] %s' % (self.name, msg), *args, **kwargs)


class FacedancerBasicScheduler(object):
    """
    Most basic scheduler for Facedancer devices-- and the schedule which is
    created implicitly if no other scheduler is provided. Executes each of its
    tasks in order, over and over.
    """

    def __init__(self,phy):
        self.tasks = []
        self.phy=phy


    def add_task(self, callback):
        """
        Adds a facedancer task to the scheduler, which will be called
        repeatedly according to the internal scheduling algorithm

        callback: The callback to be scheduled.
        """
        self.tasks.append(callback)


    def run(self):
        """
        Run the main scheduler stack.
        """

        while True:
            for task in self.tasks:
                task()
            if self.phy.should_stop_phy():
                break
