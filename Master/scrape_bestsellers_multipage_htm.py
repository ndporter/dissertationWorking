#-*- coding: utf-8 -*-
"""
## Parse bestsllers.htm into table bestsellers.tsv
## Modified 2016-10-10
## Nathaniel Porter

"""

import re, os, glob

#######################################	
##############FUNCTIONS################
#######################################

#Locate, change to, and save box sync dir to variable (NDP only)
#Still need to change wd in exec code
def getboxdir():
	try:
		dir = r"C:\Users\Nathaniel\Box Sync"
		os.chdir(dir)
	except:
		try:
			dir = r"C:\Users\natha\Box Sync"
			os.chdir(dir)
		except:
			try:
				dir = r"C:\BoxSyncNathan\Box Sync"
				os.chdir(dir)
			except:
				print 'Box Sync directory not found - please correct'
				raise SystemExit
	return dir
    
#######################################	
##############EXECUTABLE###############
#######################################

###Preliminaries
#Set working directories
boxDir = getboxdir() #works for desktop, laptop, oswald
mainDir = r'\Dissertation 2017\Data' #main working directory
inSubDir = r'\Original\Amazon html files' #location of input files
outSubDir = r'\Master' #desired output location
inPath = boxDir+mainDir+inSubDir
outPath = boxDir+mainDir+outSubDir
os.chdir(outPath) #sets os path to output
filelist = glob.glob(os.path.join(inPath,'*bestsellers.htm')) #uses inpath for input
books = []

for fullfile in filelist:
    print fullfile
    filename = os.path.basename(fullfile).split('.')
    topic = filename[0]
    date = filename[1]
    with open(fullfile, 'r') as f:
        readfile = f.read()
        pagefile = filter(None, re.split('\#{1,}page:\s[1-5]\#{1,}', readfile))

        for i in range(0, len(pagefile)):
            head, sep, tail = pagefile[i].partition('itemImmersion')
            head, sep, tail = tail.partition('zg_page1')
            pagelist = head.split('zg_clear')
            del pagelist[-1]
            
            for p in range(0, len(pagelist)):
                pagelist[p] = pagelist[p].replace('\r', '').replace('\n', '')
                # book = []
                rank = 'NA'
                asin = 'NA'

                head, sep, tail = pagelist[p].partition('zg_rankNumber">')
                head, sep, tail = tail.partition('.')
                if head:
                    rank = head

                head, sep, tail = pagelist[p].partition('/dp/')
                head, sep, tail = tail.partition('/ref')
                if head:
                    asin = head

                books.append((asin, topic, rank))



output = open('bestsellers.tsv', 'w+')
print >> output, 'asin\ttopic\trank'
for i in range(0, len(books)):
	print >> output, books[i][0]+'\t'+books[i][1]+'\t'+books[i][2]
output.close()






