'''
Created on 2011/11/13

@author: ksj
'''
class NoUseDataObj(object):
    ''' Use for replace GUI's function when
        not use GUI
    '''
    def __init__(self):
        self.label_name = ""
    def setCurrentProgress(self, value=None, text=None):
        pass
    def setProgressRange(self, min, max):
        pass
    def setProgressAutoClose(self,flag):
        pass
    def wasProgressCanceled(self):
        return False
    def getProgressText(self):
        return ""
        