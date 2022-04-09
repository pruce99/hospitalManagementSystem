from django.test import TestCase

# Create your tests here.
import threading
import time
import multiprocessing


def test(i):
    print('start', i)
    exit()
    print('end', i)


timer = threading.Timer(5, test, args=[1])
timer.start()
exit()
time.sleep(10)
print('slept')
timer.cancel()
