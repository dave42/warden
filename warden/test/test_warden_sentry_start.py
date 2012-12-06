import os
import sys
import time
import socket
import shutil
import unittest
import tempfile

test_dir = os.path.dirname(os.path.abspath(__file__))   # this is the test dir
warden_dir = os.path.dirname(test_dir)                  # warden root
sys.path.insert(0, warden_dir)

from warden_sentry import SentryManager

temp_dir = tempfile.mkdtemp()



class WardenSentryStartTestCase(unittest.TestCase):

    def test_sentry(self):
        print('Copying sample database into %s' % os.path.join(temp_dir, 'sentry.db'))
        shutil.copy2(os.path.join(test_dir, 'conf', 'sentry.db'),os.path.join(temp_dir, 'sentry.db'))

        sm = SentryManager(os.path.join(temp_dir, 'sentry.conf.py'), overwrite=True)

        sm.start_sentry()
        self.assertTrue(self.waitforsocket('localhost',9000,20,2))
        sm.stop_sentry()

    def waitforsocket(self, host, port, timeout=300, sleeptime=5):
        start = time.time()
        while (time.time()-start)<timeout:
            try:
                s = socket.create_connection((host, port), timeout)
                s.close()
                print('Success')
                return True

            except Exception as e:
                print(e)

            time.sleep(sleeptime)
        print('Failed')
        return False

if __name__=='__main__':
    unittest.main()
