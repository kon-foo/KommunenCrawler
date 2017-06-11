'''Folgender Code stammt aus: https://gist.github.com/macieksk/9743413
und wurde dort am 29.11.2012 vom User: Maciek Sykulski (https://gist.github.com/macieksk) veröffentlicht.
Er wurde meinerseits nur leicht für Python3 modifiziert.'''
from queue import PriorityQueue
import heapq


class UniquePriorityQueueWithReplace(PriorityQueue):

    def _init(self, maxsize):
        PriorityQueue._init(self, maxsize)
        self.values = dict()
        self.size_diff = 0

    def _put(self, item):
        heappush=heapq.heappush
        if item[1] not in self.values:
            self.values[item[1]] = [1,1,True]
            PriorityQueue._put(self, (item,1))
        else:
            validity = self.values[item[1]]
            validity[0] += 1   #Number of the valid entry
            validity[1] += 1   #Total number of entries
            if validity[2]:    #Is this a replace move?
                self.size_diff += 1
            validity[2] = True
            PriorityQueue._put(self, (item,validity[0]))

    def _get(self):
        heappop=heapq.heappop
        while True:
            item,i = PriorityQueue._get(self)
            validity = self.values[item[1]]
            if validity[1] <= 1:
                del self.values[item[1]]
            else:
                validity[1] -= 1    #Reduce the count
            if i == validity[0]:
                validity[2]=False
                return item
            else:
                self.size_diff -= 1

    def _qsize(self,len=len):
        return len(self.queue)-self.size_diff

    def task_done(self):
        """Changed for proper size estimation"""
        self.all_tasks_done.acquire()
        try:
            #Here
            unfinished = self.unfinished_tasks-self.size_diff - 1
            if unfinished <= 0:
                if unfinished < 0:
                    raise ValueError('task_done() called too many times')
                self.all_tasks_done.notify_all()
            #And here
            self.unfinished_tasks = unfinished+self.size_diff
        finally:
            self.all_tasks_done.release()





#
# class UniquePriorityQueue(PriorityQueue):
#     def _init(self, maxsize):
# #        print 'init'
#         PriorityQueue._init(self, maxsize)
#         self.values = set()
#
#     def _put(self, item, heappush=heapq.heappush):
#         better = [uniq for uniq in self.values if uniq[1] == item[1] and uniq[0] < item[0]]
#         if not better:
#             self.values.add((item[0],item[1]))
#             PriorityQueue._put(self, item)
#
#
#     def _get(self, heappop=heapq.heappop):
# #        print 'get'
#         item = PriorityQueue._get(self)
# #        print 'got',item
#         self.values.remove(item)
#         return item
#
# if __name__=='__main__':
#     import random, string, time, threading
#
#     u = UniquePriorityQueueWithReplace()
#     allqsize = []
#
#
#     def printer():
#         if not len(allqsize) == 0:
#             print(allqsize.pop())
#         threading.Timer(1, printer)
#         return
#
#     def testqueue():
#         u.put((random.randint(0,9), randomword()))
#         u.put((random.randint(0,9), randomword()))
#         #a = u.get()
#         #u.put((random.randint(0,9), a[1]))
#         u.task_done()
#         print(u.qsize())
#         time.sleep(0.1)
#         return
#
#     def randomword():
#         length = 5
#         return ''.join(random.choice(string.ascii_lowercase) for i in range(length))
#
#
#     printer()
#
#     for _ in range(0,1000000):
#         t = threading.Thread(target=testqueue)
#         t.deamon = True
#         t.start()
