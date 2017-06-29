# -*- coding: utf-8 -*-
"""

Created: 2016-08-28
Modified: 2016-10-12
Author: Nathaniel Porter
Purpose: Use LDA to reduce dimensionality of Amazon KWs and code all books as evangelical or mainline

LDA workflow based on https://rstudio-pubs-static.s3.amazonaws.com/79360_850b2a69980c4488b1db95987a24867a.html

"""

#imports
#from nltk.tokenize import RegexpTokenizer
from stop_words import get_stop_words
from nltk.stem.porter import PorterStemmer
from gensim import corpora
import gensim
import os
import pandas as pd
import numpy as np
import re

###Defined functions
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

#append list of words in keyword strings to texts
def kw_texts_append(doc, textslist):    
	#convert to all lower
	raw = doc.lower()
	#split string on anything except alphanumeric, hypen or apostrophe
	kws = re.split('[^\\w\'-]+', raw)       
	#remove numbers, words less than 3 letter (usually initials), and custom stopwords from list    
	kws = [x for x in kws if not(x.isdigit() or len(x) < 3 or x == 'amp' or x == 'ebook' or x == 'e-books')]
	#remove standard english stopwords
	stopped_tokens = [i for i in kws if not i in en_stop]
	# stem tokens
	stemmed_tokens = [p_stemmer.stem(i) for i in stopped_tokens]
	#append to texts  
	textslist.append(stemmed_tokens)
	
#LDA functions not above
#Read standard English stopwords
en_stop = get_stop_words('en')
# Create p_stemmer of class PorterStemmer
p_stemmer = PorterStemmer()

#################EXECUTABLE###################

###Preliminaries
#Set working directories
boxDir = getboxdir() #works for desktop, laptop, oswald
mainDir = r'\Diss\Bootcamp 2016 October\Data' #main working directory
outSubDir = r'\Output' #desired output location
outPath = boxDir+mainDir+outSubDir
os.chdir(outPath) #sets os path to output
#Set seed for LDA
np.random.seed(654321)

#Read in Keywords
kwDf = pd.read_table('attributes.tsv')
kwDf = kwDf.drop_duplicates(subset='asin')

#Create list of kwSets
doc_set = list(kwDf['kwstring'])

# list for tokenized documents in loop
texts = []

# loop through document list
for i in doc_set:
    kw_texts_append(i, texts)

# turn our tokenized documents into a id <-> term dictionary
dictionary = corpora.Dictionary(texts)

# convert tokenized documents into a document-term matrix
corpus = [dictionary.doc2bow(text) for text in texts]

# generate LDA model
model = gensim.models.ldamodel.LdaModel(corpus, num_topics=10, id2word = dictionary, passes=100)
model.save('lda.model') #save model to disk
#OLDprint(lda.print_topics(num_topics=10, num_words=20))
# print top 20 keywords for topics
#for i in range(0, model.num_topics-1):
#    print model.print_topic(i, topn=20)

#Calculate topic probability by document
doctops_tuples = []
for n in range(len(corpus)):
    doctops_tuples.append(model.get_document_topics(corpus[n]))
#Dataframe of probabilities (row=doc, col=topic, val=prob)
doctops = pd.DataFrame(columns = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'], index=np.arange(len(doctops_tuples)))
for n in range(len(doctops_tuples)):
    rowdict = {'0': '0', '1': '0', '2':'0', '3':'0', '4':'0', '5': '0', '6': '0', '7':'0', '8':'0', '9':'0'}
    for x in range(len(doctops_tuples[n])):
        key = str(doctops_tuples[n][x][0])
        value = doctops_tuples[n][x][1]
        rowdict[str(key)] = str(value)
    for key, value in rowdict.iteritems():
        doctops[key][n] = value

#destring doctops
doctops = doctops.apply(lambda x: pd.to_numeric(x, errors='raise'))

#check correlations and terms
#covs = np.cov(doctops, rowvar=0)
#corrs = np.corrcoef(doctops, rowvar=0)

#save persistent copy (probabilities differ slightly each time they're calculated)

##Supplement data
#Import publisher data from csv
pubDf = pd.read_csv('codedPublishers.csv')

#Merge publisher classes onto books
toMerge = pd.DataFrame(data=[pubDf['Publisher'], pubDf['Class']]).T
toMerge = kwDf.merge(toMerge, how='left', left_on='publisher', right_on='Publisher')
toMerge = toMerge.drop(['Publisher', 'kwstring'], axis=1)
#Merge topic probabilitiess on
toMerge = toMerge.merge(doctops, left_index=True, right_index=True)
#overall mean topic probability by topic (sums to 1)
toMerge.mean()

##Scatterplots of prob(topic) by topic number within publisher classes

#group by class
gByPubClass = toMerge.groupby('Class')
#Counts by class
gByPubClass.size()
#Mean likelihood of topic by class
gByPubClass.mean()
#Reshape topic probabilities to long
kwLim = pd.DataFrame([toMerge['Class'], toMerge['0'], 
                      toMerge['1'], toMerge['2'], toMerge['3'], toMerge['4'], 
                      toMerge['5'], toMerge['6'], toMerge['7'], toMerge['8'], toMerge['9']]).T
kwLim = pd.melt(kwLim, id_vars='Class')
kwLim['value'] = pd.to_numeric(kwLim['value'])

"""
#Swarm plots of each type of classification
import seaborn as sns
sns.set(style="whitegrid", color_codes=True)
#Plot commented to save processing time subsequent (saved to file)
sns.factorplot(x='variable', y='value', col='Class', data=kwLim, kind='swarm')


#Assign books deterministically to most likely topic
detAssign =  pd.DataFrame([toMerge['Class'], toMerge['0'], 
                      toMerge['1'], toMerge['2'], toMerge['3'], toMerge['4'], 
                      toMerge['5'], toMerge['6'], toMerge['7'], toMerge['8'], toMerge['9']]).T
#idxmax populates column name where max value occurs
detAssign['hiTop'] = detAssign[['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']].idxmax(axis=1)
##compare distribution of hiTop to ByTopic means
#Group by topic
gByTopic = kwLim.groupby('variable')
#overall distributions by topic
gByTopic.mean()
#hiTop
detAssign.groupby('hiTop').size()/1288
#Category 6 is underrepresented in deterministic assignment (Roman Catholic is key, so less important)
"""

#Assign books to top likelihood of mainline or evangelical based on overall topics and class
#USE MI in STATA
toMerge.to_csv('forStataImpute.csv')
