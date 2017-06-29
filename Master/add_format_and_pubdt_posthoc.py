#-*- coding: utf-8 -*-
"""
## Retrieve additional attributes from pages.htm (to prevent needing to impute)
## Modified 2017-03-12
## Nathaniel Porter

#Output variables#
attributes
    asin
    title
    author
    publisher
    prdtype
    salesrank
    isbn10
    isbn13
    Keywords
edges
    asin
    recommendations and ranks (variables r1 to r100)
"""

import os, HTMLParser, re
from glob import glob

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

##Create edgelist
#Writes outfile as new edgelist file
#Line Output is a tabbed edgelist to append to file for lines matched, otherwise nothing
#Does not work for non-physical media (different prdtype of recommendation lists)
def get_edges(page, out):
    pattern = r'        <div data-a-carousel-options='
    for line in page.readlines():
        if line.startswith(pattern):
            asin = get_asin(line)
            if asin == '':
                pass
            else:
                ties = get_ties(line)
                out.write('\n'+asin)
                for e in ties:
                    out.write('\t'+e)
        else:
            pass
        
def get_ties(line):
    head, sep, tail = line.partition('id_list&quot;:[&quot;')
    head, sep, tail = tail.partition('&quot;]')
    return head.split('&quot;,&quot;')

def get_asin(line):
    head, sep, tail = line.partition('baseAsin&quot;:&quot;')
    head, sep, tail = tail.partition('&quot;')
    #if head == ''
    #    print 'Problem with '+topic+' page number '+i-1
    return head

##Subdivide page into original product pages
def subpages(file):
    #pages = file.split(r'<!doctype html') #split multifile into single pages
    readfile = file.read()
    pages = readfile.split(r'<!doctype html') #split multifile into single pages
    #filter(None, re.split('\#{1,}page:\s[1-5]\#{1,}', readfile))    
    return pages
##Create atributes list
#uses subdivision equal to one product page
def get_attributes(page, out):
    #assign each value to missing each page
    asin, title, author, publisher, pubdt, prdtype, salesrank, isbn10, isbn13, authorcount, kwstring = ('','','','','O',0,'','',0,'')
    lines = page.split('\n')
    for line in lines:        
        #asin
        if line.startswith(r'        <div data-a-carousel-options='):
            if asin == '':
                asin = get_asin(line)
        #title
        elif '<span id="productTitle" class="a-size-large">' in line:
            title = get_ta(line)
            #optional shortener
            #attdict['title'] = shorten_title(attdict['title'])       
        #author
        elif 'class="a-link-normal contributorNameID"' in line or 'byline_sr_book_1' in line:
            authorcount += 1
            if authorcount == 1:
                author = get_ta(line)
        #publisher
        elif 'Publisher:' in line:
            publisher =  get_isbnp(line)
            psplit = re.split('( \(|;)', publisher) #search simultaneously for ' (' and ';' to separate publisher from date/edition
            publisher = psplit[0]
        #pubdt
        elif r'<span class="a-size-medium a-color-secondary a-text-normal">&ndash;' in line:
            head,sep,tail = line.partition(r'&ndash; ')
            head,sep,tail = tail.partition(r'</')
            pubdt = head
        #prdtype
        elif 'Paperback:' in line or r'<b>Paperback' in line:
            prdtype = 'P'
        elif 'Hardcover:' in line:
            prdtype = 'H'
        elif 'Print Length:' in line:
            if asin.startswith('B'): #to ensure books aren't falsely changed to Kindle
                prdtype = 'K'
        elif 'Listening Length' in line:
            prdtype = 'A'
        #salesrank
        elif 'See Top 100 in' in line or 'See Top 100 Paid in' in line:
            salesrank = get_srank(line)
        #isbn10 and isbn13 (for matching editions to external databases)
        elif 'ISBN-10' in line or 'Page Numbers Source ISBN' in line:
            isbn10 =  get_isbnp(line)
        elif 'ISBN-13' in line:
            isbn13 =  get_isbnp(line)
        #keywords
        elif r'<meta name="keywords"' in line:
            head, sep, tail = line.partition(r'content="')
            head, sep, tail = tail.partition(r'" ')
            kwstring = head
        else:
            pass
    #backup asin for items without a carousel
    if asin == '':
        for line in lines:
            if 'link rel="canonical"' in line:
                head, sep, tail = line.partition('dp/')
                head, sep, tail = tail.partition('"')
                asin = head
            else:
                pass
    #write page results to outfile before resetting for next page
    if asin != '':
        out.write('\n')
        try:
            out.write(asin+'\t'+title+'\t'+author+'\t'+publisher+'\t+'pubdt'+\t+'+prdtype+'\t'+str(salesrank)+'\t'+isbn10+'\t'+isbn13+'\t'+str(authorcount)+'\t'+kwstring)
        except: #prints lines with special characters etc to screen to be added to file manually
            print 'Case contains special characters - add by hand'
            print('\n'+asin+'\t'+title+'\t'+author+'\t'+publisher+'\t+'pubdt'+\t'+prdtype+'\t'+str(salesrank)+'\t'+isbn10+'\t'+isbn13+'\t'+str(authorcount)+'\t'+kwstring)

##Individual Attributes
#ISBN10 ISBN13 Publisher
def get_isbnp(line):
    head, sep, tail = line.partition('/b> ')
    head, sep, tail = tail.partition('<')
    return head
#Title Author    
def get_ta(line):
    head, sep, tail = line.partition('>')
    head, sep, tail = tail.partition('<')
    return head
#Salesrank
def get_srank(line):
    head, sep, tail = line.partition(' (<')
    if head.startswith('#'):
        head, sep, tail = head.partition(' ')
    else:
        head, sep, tail = head.partition('/b> ')
        head, sep, tail = tail.partition(' ')
    temp = head.strip('#')
    temp = temp.replace(',', '')
    return int(temp)

##Remove escapes (adapted from 'Neil Aggarwal' at stackoverflow 2087370)
def rem_esc(strname):
    h = HTMLParser()
    return h.unescape(strname)
  
    
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

#Make list of all input files (product pages, up to 100 per file)
filelist = glob(os.path.join(inPath,'*pages.htm')) #uses inpath for input

###Asins and Edges
with open('edges.tsv', 'w') as outfile:
    tnames = ''
    for num in range(1,101):
        tnames = tnames+'\tr'+str(num)
    outfile.write('asin'+tnames)
    for fullfile in filelist:
        print fullfile
        with open(fullfile, 'r') as f:
            get_edges(f, outfile)       

##Attributes of products
with open('attributes.tsv', 'w') as outfile:
	outfile.write('asin\ttitle\tauthor\tpublisher\tpubdt\tprdtype\tsalesrank\tisbn10\tisbn13\tauthorcount\tkwstring')
	for fullfile in filelist:
		with open(fullfile, 'r') as f:
			for page in subpages(f):
				get_attributes(page, outfile)

        