import os
import shutil


#if already dest_d file exits, delete and then create
path = os.path.join('{0}\\Logs_folder\\'.format(os.getcwd().split('D')[0]))
files = os.listdir(path)
for f in files:
        print(f)




 """" 
    if f == 'LTE_TX_Band4_max':
         print("file exists, removing the file log")
         shutil.rmtree(os.path.join('{0}\\Logs_folder\\'.format(os.getcwd().split('D')[0]), 'LTE_TX_Band4_max'))
         # Creating directory for results
         dest = os.path.join('{0}\\Logs_folder\\'.format(os.getcwd().split('D')[0]),
                             'LTE_TX_Band4_max')
         # os.makedir(dest)1
         dest_d = dest.replace('\\', '\\\\')
    else:
        dest = os.path.join('{0}\\Logs_folder\\'.format(os.getcwd().split('D')[0]),
                            'LTE_TX_Band4_max')
        # os.makedir(dest)1
        dest_d = dest.replace('\\', '\\\\')
        
"""






