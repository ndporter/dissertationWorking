#-*- coding: utf-8 -*-
"""
## Read attributes and edgelist for copurchase data and output 50/50 split dataset to train.dat and test.dat
## Modified 2016-02-28
## Nathaniel Porter

"""

import os
import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None  # default='warn' this disables chained reference warnings    

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
	
#takes mindel and maxdel for range of topic numbers to delete
def selecttopics(df, mindel, maxdel):
    temp = df #make a local copy
    try:
        temp.rename(columns = {'variable':'topic'}, inplace = True)
    except:
        pass
    try:
        temp['topic'] = temp['topic'].apply(lambda x: int(x.lstrip('topic')))
    except:
        pass
    #delete topics not of interest
    for i in range(mindel,maxdel+1):
        temp = temp[temp['topic']!=i]
    #calculate new count
    #temp['topct']=temp.groupby('asin').size()
    #temp = temp[temp['topct']>0]    
    return temp
	
#Keep only edges in the attribute dataset
def selectedges(edgedf,attdf,col):
    try:
        temp = attdf[['asin','title']]
    except:
        temp = attdf[['asin']]
    newedges = edgedf.merge(temp, how='inner', left_on=col, right_on='asin')
    return newedges

#Calculate Zipfian distributation as proportional to rank 1
def zipf(x, tau):
    f = 1/(x**(1/tau))
    return f
    
    
#######################################	
##############EXECUTABLE###############
#######################################


###Preliminaries###

#Set working directories
boxDir = getboxdir() #works for desktop, laptop, oswald
mainDir = r'\Dissertation 2017\Data\Master' #main working directory
outSubDir = r'\tempOutput' #location for output data
dataPath = boxDir+mainDir
outPath = dataPath+outSubDir

#Read input data on books (imputed attributes + edges)
os.chdir(dataPath) #sets os path to data
attributes = pd.read_table('AllAttributesWithTopicsLong.tsv')
edges = pd.read_table('edges.tsv')
os.chdir(outPath) #sets os path to output


###Create reduced attributes (case=book) dataframe of only denominational topics###

#Remove kindle and Audible books to keep all salesranks on the same scale
attributes = attributes[attributes['prdtype']!='A']
attributes = attributes[attributes['prdtype']!='K']
#select topics
denAttsI = selecttopics(attributes,9,20)
#Check number needing weights
#denAttsI.groupby('asin').size()[denAttsI.groupby('asin').size()>1]
##Manually select best match given there are only three
#0253218683 is clearly SDA (8) not Baptist (2) = 8
#0805464166 is a Baptist (2) case against Calvinist doctrine (3) = 2
#0828020124  is also SDA (8) not Baptist (2) = 8
denAttsI.drop([891,1001,857],inplace=True) #used indices to avoid NOT BOTH conditional
#Remove surplus variables
denAttsI.drop(['title','author','publisher','prdtype','topct','topWt'],axis=1, inplace=True)


##Create edges dataframe containing only edges where both partners are in denAttsI###

#reshape edges to long
edgesLong = pd.melt(edges, id_vars='asin')
#remove r's and convert to int
edgesLong['variable'] = edgesLong['variable'].apply(lambda x: int(x.lstrip('r')))
##remove lines with asins not in data and missing asins
edgesLong = selectedges(edgesLong,denAttsI,'asin')
edgesLong = selectedges(edgesLong,denAttsI,'value')
#cleanup
edgesLong.rename(columns={'asin_x':'source','value':'target','variable':'copRank'}, inplace=True)
edgesLong.drop(['asin_y'],axis=1,inplace=True)

##Create limited denoms dataframe with only asins in denoms edge data
def selectatts(edgedf,attdf):
    temp = edgedf[['source']]
    newatts = attdf.merge(temp, how='inner', left_on='asin', right_on='source')
    return newatts
denAttL = selectatts(edgesLong,denAttsI).drop_duplicates()

###generate dataframe to export to svm .dat file###
#Space-delimited format for SVMrank
#no header
"""
#Source ASIN
qRevRank qid:id 1:sSr 2:tSr 3:sPubDt 4:tPubDt 5:stDiffSr 6:diffPubDt 7:sB4t 8:sB4txDiffPubDt
"""

##Create limited version to test output (no pub dates w/out scraping more)
#qRevRank qid:id 1:sSr 2:tSr 3:stRatioSr

#Create copy of edges to work from
svmEdges = edgesLong
#reverse code co-purchase rank as (101-rank)
svmEdges['qRevRank'] = 101 - svmEdges['copRank']

#Append source and target salesranks
#Function to append a given attribute for both source and target to edgelist
#Use different function for imputed values (from Final...line194ff)
def scTgattribAppend(attDF,edgeDF,attribute):
	temp = pd.concat([attDF['asin'],attDF[attribute]],axis=1)
	tempedges = edgeDF.merge(temp,left_on='source',right_on='asin')
	tempedges.rename(columns={attribute:'source'+attribute},inplace=True)
	tempedges = tempedges.merge(temp,left_on='target',right_on='asin')
	tempedges.rename(columns={attribute:'target'+attribute},inplace=True)
	tempedges.drop(['asin_x','asin_y'],axis=1,inplace=True)
	return tempedges
svmEdges = scTgattribAppend(denAttsI,svmEdges,'salesrank')
svmEdges.rename(columns={'sourcesalesrank':'sSr','targetsalesrank':'tSr'},inplace=True)

#Calculate difference of salesranks (ratio doesn't work well with additive since range is restricted on one end)
#Values are positive when source has higher value of rank (e.g. lower sales) than target
svmEdges['stDiffSr'] = svmEdges['sSr']-svmEdges['tSr']

#Sort both frames
denAttL.sort_values(['asin'],axis=0,ascending=False,inplace=True)
svmEdges.sort_values(['source','qRevRank'],axis=0,ascending=False,inplace=True)

#remove queries with 3 or less constituents as at least one (train or test) won't be able to compare
counts = svmEdges['source'].value_counts()
svmEdges =  svmEdges[svmEdges['source'].isin(counts[counts > 3].index)]

##Generate sequential recommender id numbers for qid
#id in attributes (so unique by source)
denAttL['qid']=0
for n in range(len(denAttL)):
    denAttL['qid'].iloc[n] = n+1
#merge onto svmEdges
qid = denAttL[['qid','asin']]
"""
nest0out = svmEdges.merge(qid,how='left',left_on='source',right_on='asin')
nest0out = nest0out.merge(qid,how='left',left_on='target',right_on='asin')
nest0out.drop(['source','target','asin_x','asin_y',],axis=1,inplace=True)
nest0out.rename(columns={'qid_x':'qid','qid_y':'target'},inplace=True)

#Output to .dat
#qRevRank qid:id 1:sSr 2:tSr 3:stDiffSr
#generate qid and minimal df
nest0out = nest0out[['qRevRank','qid','sSr','tSr','stDiffSr']]

#output
nest0out.to_csv('nest0.csv',sep=',',header=True,index=False)


###ALL SETS OF POSSIBLE FEATURES FOR SVM/RIDGE###
#0 Non-topical
4	sSr,tSr,
#1a Source Topics
7	sB,sPR,sL,sM,sP,sQ,sSDA,
#1b Target Topics
7	tB,tPR,tL,tM,tP,tQ,tSDA,
#2 Evangelical (source, target,interaction)
3	sEv,tEv,sEv*tEv,
#3a (#1)*(#2.1)
7	sB*sEv,sPR*sEv,sL*sEv,sM*sEv,sP*sEv,sQ*sEv,sSDA*sEv,
#3b (#1)*(#2.2)
7	tB*tEv,tPR*tEv,tL*tEv,tM*tEv,tP*tEv,tQ*tEv,tSDA*tEv,
#4 = #1a*12b
7	sB*tB,sB*tPR,sB*tL,sB*tM,sB*tP,sB*tQ,sB*tSDA,
7	sPR*tB,sPR*tPR,sPR*tL,sPR*tM,sPR*tP,sPR*tQ,sPR*tSDA,
7	sL*tB,sL*tPR,sL*tL,sL*tM,sL*tP,sL*tQ,sL*tSDA,
7	sM*tB,sM*tPR,sM*tL,sM*tM,sM*tP,sM*tQ,sM*tSDA,
7	sP*tB,sP*tPR,sP*tL,sP*tM,sP*tP,sP*tQ,sP*tSDA,
7	sQ*tB,sQ*tPR,sQ*tL,sQ*tM,sQ*tP,sQ*tQ,sQ*tSDA,
7	sSDA*tB,sSDA*tPR,sSDA*tL,sSDA*tM,sSDA*tP,sSDA*tQ,sSDA*tSDA,
#5 = #3a*#3b Denom * Evangelical
	=49
#Excluded for now (sticking to rankings)
2  sPubDt,tPubDt,
4	stRatioSr,diffPubDt,sB4t,sB4t*diffPubDt
"""

##Append additional variables for more datasets
#Base data to append on
#dataCore = svmEdges.merge(qid,how='left',left_on='source',right_on='asin')
#dataCore = dataCore.merge(qid,how='left',left_on='target',right_on='asin')
#Append all variables to source and target
dataCore = svmEdges.merge(denAttL,how='left',left_on='source',right_on='asin')
dataCore = dataCore.merge(denAttL,how='left',left_on='target',right_on='asin')


#Clean up with renames
dataCore.drop(['qid_y','stDiffSr','asin_x','asin_y','qRevRank','salesrank_x','salesrank_y','value_x','source_y','value_y','source'],axis=1,inplace=True)
dataCore.rename(columns={'source_x':'source','copRank':'coPr','qid_x':'query'},inplace=True)

#Temporarily only rename a single imputation of Evangelical
dataCore.rename(columns={'_1_classEvM_x':'sEvI1','_1_classEvM_y':'tEvI1'},inplace=True)
#Fix format for topics
dataCore = dataCore.dropna(subset=['topic_y'])
dataCore.topic_y = dataCore.topic_y.apply(lambda x:int(x))

#Add same topic
dataCore['sTopEqTTop'] = np.where(dataCore['topic_x']==dataCore['topic_y'],1,0)

#Recode topic_x and topic_y
dataCore = pd.get_dummies(dataCore, columns=['topic_x','topic_y'],prefix=['sDen', 'tDen'])
#Rename dummies to denote denomination
topics = {'AE':1,'B':2,'CP':3,'L':4,'M':5,
           'P':6,'Q':7,'SDA':8}
for letter in ['s','t']:
	for key,value in topics.iteritems():
		orig = letter+'Den_'+str(value)
		new = letter+'Den'+key
		dataCore.rename(columns={orig:new},inplace=True)
        #Add Ev*Topic (easier while still in loop)
        inter = new+'ByEv'
        evvar = letter+'EvI1'
        dataCore[inter] = dataCore[new]*dataCore[evvar]
        
#Add Ev*Ev
dataCore['sEv1ByTEv1']=dataCore['sEvI1']*dataCore['tEvI1']

#Construct datasets for analyzing single-book sales
#topic
salesByEv = dataCore[['source','sSr','sEvI1','sDenB','sDenCP','sDenL','sDenM','sDenP','sDenQ','sDenSDA']]

##Construct sets for each model by selecting a subset of variables
#Model 2 (ranks, topics, evangelical and limited interactions)
data2 = dataCore[['source','target','coPr','query','sSr','tSr',
				  'sDenB','sDenCP','sDenL','sDenM','sDenP','sDenQ','sDenSDA',
				  'tDenB','tDenCP','tDenL','tDenM','tDenP','tDenQ','tDenSDA',
				  'sEvI1','tEvI1','sEv1ByTEv1','sTopEqTTop'
				  ]]
#Model 1 (ranks and topics)
data1 = dataCore[['source','target','coPr','query','sSr','tSr',
				  'sDenB','sDenCP','sDenL','sDenM','sDenP','sDenQ','sDenSDA',
				  'tDenB','tDenCP','tDenL','tDenM','tDenP','tDenQ','tDenSDA'
				  ]]
#Model 0 Baseline (ranks only)
data0 = dataCore[['source','target','coPr','query','sSr','tSr',
				  ]]

#Output files for each model
def dataOut(df,name):
	df.to_csv(name,sep=',',header=True,index=False)
models = {'data0':data0,'data1':data1,'data2':data2,'salesByEv':salesByEv}
for key,value in models.iteritems():
	name = key+'.csv'
	dataOut(value,name)

#########################################
###############JUST IN CASE##############
#########################################
"""
nest0out['qid'] = nest0out['qid'].apply(str)
nest0out['qid'] = nest0out['qid'].apply(lambda x:r'qid:'+x)
nest0out['sSr'] = nest0out['sSr'].apply(str)
nest0out['sSr'] = nest0out['sSr'].apply(lambda x:r'1:'+x)
nest0out['tSr'] = nest0out['tSr'].apply(str)
nest0out['tSr'] = nest0out['tSr'].apply(lambda x:r'2:'+x)
nest0out['stDiffSr'] = nest0out['stDiffSr'].apply(str)
nest0out['stDiffSr'] = nest0out['stDiffSr'].apply(lambda x:r'3:'+x)
"""
"""
#Small training and testing datasets to figure out how it works
subsetData = svmEdges.merge(qid,how='left',left_on='source',right_on='asin')
subsetData = subsetData.merge(qid,how='left',left_on='target',right_on='asin')
subsetData.drop(['source','target','asin_x','asin_y',],axis=1,inplace=True)
subsetData.rename(columns={'qid_x':'qid','qid_y':'target'},inplace=True)
trainSubset = subsetData.loc[subsetData['qid'].isin(range(1,21))]
testSubset = subsetData.loc[subsetData['qid'].isin(range(21,41))]
#defined routine for cleaning data to SVM
def tosvm(df,outfile,fields):
    allfields = ['qRevRank','qid']+fields
    temp = df[allfields]
    temp['qid'] = temp['qid'].apply(str)
    temp['qid'] = temp['qid'].apply(lambda x:r'qid:'+x)
    n = 0    
    for field in fields:
        n+=1
        fnum = str(n)+r':'        
        temp[field] = temp[field].apply(str)
        temp[field] = temp[field].apply(lambda x:fnum+x)
    temp.to_csv(outfile,sep=' ',header=False,index=False)
    
#output test data
tosvm(trainSubset,'trainSubset.dat',['sSr','tSr','stDiffSr'])
tosvm(testSubset,'testSubset.dat',['sSr','tSr','stDiffSr'])

###Cleaning topics and numbers for usability
#Create topic numbers
#Dictionary to translate
topDict = {'Anglican-Episcopalian':1,'Baptist':2,'Calvinist-Presbyterian':3,'Lutheran':4,'Methodist':5,
           'Pentecostal':6,'Quaker':7,'Seventh-Day Adventist':8,'Catholicism':9,
           'Bible Study & Reference':11,'Christian Biographies':12,'Christian History':13,'Christian Theology':14,
           'Literature, Fiction & Romance':15,'Christian Living':16,'Worship & Devotion':17,'Churches & Church Leadership':18,
           'Ministry & Evangelism':19}
"""