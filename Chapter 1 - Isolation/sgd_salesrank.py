# -*- coding: utf-8 -*-
"""
Created on Mon Mar 06 13:55:08 2017

@author: natha
"""

#import json
import os
import itertools
import numpy as np
import pandas as pd
from scipy import stats
import pylab as pl
from sklearn import svm, cross_validation, preprocessing

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

#Subroutine to generate train and test data from larger dataframe
#use sSr,tSr (sales features) coPr (ranks) for ranks
#use sSvol,tSvol (sales features) coPvol (ranks) for values
def genTrainTest(df,features,queries,ranks,ts=.5):
	#features
	X =df[features]
	X = np.asarray(X)
	#X=np.asarray(X)
	#X=np.asarray(data0['sSvol'],data0['tSvol'])
	#queries
	blocks=np.asarray(list(df[queries]))
	#ranks
	y=np.asarray(list(df[ranks]))
	#split into test and train
	cv = cross_validation.StratifiedShuffleSplit(df[ranks],test_size=ts)
	train, test = iter(cv).next()
	X_train, y_train, b_train = X[train], y[train], blocks[train]
	X_test, y_test, b_test = X[test], y[test], blocks[test]
	#Scale features to range [0,1] in training dat
	#Mean/SD scaling doesn't make sense with so many factor variables
	#Each topic would have a different range
	scaler = preprocessing.MinMaxScaler()
	X_train = scaler.fit_transform(X_train)
	#Use same transformation on test data (may not have range from 0 to 1 in test)
	X_test = scaler.transform(X_test)
	#output
	#train = [X_train, y_train, b_train]
	#test = [X_test, y_test, b_test]
	return X_train, y_train, b_train, X_test, y_test, b_test

#Add every other item as #101 from each source
#df is dataframe to extend
#targets is col in df with asins
#sources is col in allItems with source asins
def add101s(df,dfname,targets,queries,sources):
	tempdf=df
	sourcelist = df[sources].drop_duplicates()
	svars = [col for col in list(df) if col.startswith('s')]
	tvars = [col for col in list(df) if col.startswith('t')]
	rowsToAdd = []
	for query in sourcelist:
		try:
			qSub = df[df[sources] == query]
			for target in sourcelist:
				trueQuery = qSub[queries][0]
				#if source is not in targets[query=query]
				if target in qSub[targets] or target==query:
					pass
				else:
					#dictionary of line to add (no need for order if labeled)
					linetoadd = {
						sources:query,
						targets:target,
						queries:trueQuery
						}
					try:
						targTemp = pd.DataFrame(df[df[targets]==target].iloc[[0]])
						for var in tvars:
							#print targTemp[var].iloc[0]
							if var == 'target':
								pass
							else:
								linetoadd[var]=targTemp[var].iloc[0]
								#print linetoadd
					#Except is for books that are never a target (pulls from line where source)
					except:
						targTemp=pd.DataFrame(df[df[sources]==query].iloc[[0]])
						for var in tvars:
							eqsvar = 't'+var[1:]
							targTemp[var]=targTemp[eqsvar]
							if var == 'target':
								pass
							else:
								linetoadd[var]=targTemp[var].iloc[0]
								#print linetoadd
					scTemp = pd.DataFrame(df[df[sources]==query].iloc[[0]])
					for var in svars:
						if var == 'source':
							pass
						else:
							linetoadd[var]=scTemp[var].iloc[0]
					linetoadd['coPr'] = 101
					#tempdf = tempdf.append(linetoadd,ignore_index=True)
					rowsToAdd.append(linetoadd)
					tempdf = tempdf.append(rowsToAdd)			
		except:
			pass
		return tempdf
		###NOTE: ADD INTERACTIONS LATER: FOR NOW RUN WITHOUT###
		#append a line to dataframe with
		#query = query
		#s* = s* for first instance of query
		#t* = t* for first instance of target
		#coPr = 101
		#delete interactions and calculate in this routine

#Subroutine to automate estimation of pairwise ranked SVMs from train,test data (see above)
def rankSvmEst(train,test,c=.1,krn='linear'):
	# form all pairwise combinations
	comb = itertools.combinations(range(train[0].shape[0]), 2)
	k = 0
	Xp, yp, diff = [], [], []
	#estimate model
	for (i, j) in comb:
		if train[1][i] == train[1][j] \
			or train[2][i] != train[2][j]:
			# skip if same target or different group
			continue
		Xp.append(train[0][i] - train[0][j])
		diff.append(train[1][i] - train[1][j])
		yp.append(np.sign(diff[-1]))
		# output balanced classes
		if yp[-1] != (-1) ** k:
			yp[-1] *= -1
			Xp[-1] *= -1
			diff[-1] *= -1
		k += 1
	Xp, yp, diff = map(np.asanyarray, (Xp, yp, diff))
	clf = svm.SVC(kernel=krn, C=c)
	clf.fit(Xp, yp)
	coef = clf.coef_.ravel() / np.linalg.norm(clf.coef_)
	#Run tau tests
	#omnibus
	tauOmni = tautest('svm',coef,test,True)
	#querywise
	tauQwise = tautest('svm',coef,test,False)
	#allows readable modifications to features
	return clf,coef,tauOmni,tauQwise

#Test using Tau
#args:
#type = type of coefficient ('ridge','svm')
#omnibus = True for a single Tau, false for Tau by query (default:False)
#test = test df (default:test)
#coef = coefficients (not needed for ridge) (default:coef)
def tautest(ttype,coef,test,omnibus=False):
	blockTau = []
	#omnibus
	if omnibus == True:
		if ttype == 'sgd':
			tau, p = stats.kendalltau(np.dot(test[0],coef.T), test[1])
		elif ttype == 'svm':
			tau, p = stats.kendalltau(np.dot(test[0], coef), test[1])
		else:
			print "Please specify supported type ('ridge','svm')"
			raise SystemExit
		blockTau.append([tau,p])
	else:
		#querywise
		foo = pd.Series(test[2])
		foo = foo.drop_duplicates()
		size = len(foo) #size is number of queries in test data
		if ttype == 'sgd':
			for i in range(size): #id numbering starts at 1
				tau, p = stats.kendalltau(np.dot(test[0][test[2] == i], coef.T), test[1][test[2] == i])
				blockTau.append([i,tau,p])
		else:
			for i in range(size): #id numbering starts at 1
				tau, p = stats.kendalltau(np.dot(test[0][test[2] == i], coef), test[1][test[2] == i])
				blockTau.append([i,tau,p])	#Make df for summaries	
	if omnibus==True:
		taudf = pd.DataFrame(blockTau,columns=['tau','p'])
	else:
		taudf = pd.DataFrame(blockTau,columns=['query','tau','p'])
	return taudf
	
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
os.chdir(outPath) #sets os path to output
		
data = pd.read_csv('salesByEv.csv')

#Add every other item as #101 from each source
#df is dataframe to extend
#targets is col in df with asins
#sources is col in allItems with source asins
#data2 = add101s(data,'data','target','query','source')

X_train, y_train, b_train, X_test, y_test, b_test = genTrainTest(data,['sDenB','sDenCP','sDenL','sDenM','sDenP','sDenQ','sDenSDA'],'sEvI1','sSr',ts=.5)
#rankRdg,rankRdgCoef,rankRdgTO,rankRdgTQ = rankSvmEst([X_train,y_train,b_train],[X_test,y_test,b_test])

# form all pairwise combinations
comb = itertools.combinations(range(X_train.shape[0]), 2)
k = 0
Xp, yp, diff = [], [], []
#estimate model
for (i, j) in comb:
	if y_train[i] == y_train[j] \
		or b_train[i] != b_train[j]:
		# skip if same target or different group
		continue
	Xp.append(X_train[i] - X_train[j])
	diff.append(y_train[i] - y_train[j])
	yp.append(np.sign(diff[-1]))
	# output balanced classes
	if yp[-1] != (-1) ** k:
		yp[-1] *= -1
		Xp[-1] *= -1
		diff[-1] *= -1
	k += 1
Xp, yp, diff = map(np.asanyarray, (Xp, yp, diff))

#Try SGD for larger dataset
from sklearn.linear_model import SGDClassifier
clf=SGDClassifier(loss='hinge', penalty='l2')
clf.fit(Xp,yp)
coef = clf.coef_
clf.score(Xp,yp)

#Prep to test accuracy
# form all pairwise combinations
comb = itertools.combinations(range(X_test.shape[0]), 2)
k = 0
Xp, yp, diff = [], [], []
#estimate model
for (i, j) in comb:
	if y_test[i] == y_test[j] \
		or b_test[i] != b_test[j]:
		# skip if same target or different group
		continue
	Xp.append(X_test[i] - X_test[j])
	diff.append(y_test[i] - y_test[j])
	yp.append(np.sign(diff[-1]))
	# output balanced classes
	if yp[-1] != (-1) ** k:
		yp[-1] *= -1
		Xp[-1] *= -1
		diff[-1] *= -1
	k += 1
Xp, yp, diff = map(np.asanyarray, (Xp, yp, diff))
#Test it!
clf.score(Xp,yp)
#Test it split by evangelical
#omnibus
tauOmni = tautest('sgd',coef,[X_test,y_test,b_test],True)
#querywise
tauQwise = tautest('sgd',coef,[X_test,y_test,b_test],False)
#Predict for pvp plot
predictions = pd.DataFrame(yp.T,columns=['actual'])
predictions['predicted']=0
for i in range(len(predictions)):
	predictions['predicted'][i] = np.dot(Xp[i],coef.T)
#Make pvp plot
pl.plt.figure()
pl.plt.scatter(predictions['predicted'],predictions['actual'])
#clears figure
pl.plt.clf()

#get data from crosstab (use commented line to autopopulate later)
pd.crosstab(predictions['predicted'],predictions['actual'])
#pd.crosstab(predictions['predicted'],predictions['actual'])[1][-2]
#Make list of cells in crosstab
plotlocations=[]
for i in range(-2,3):
	for j in [-1,1]:
		plotlocations.append([i,j])
#use values from crosstab for weights
sample_weights = [110076,8818,171752,53247,488841,487805,52962,171441,8742,111062]
for s in range(len(sample_weights)):
	sw[s] =  sample_weights[s]/1000
i = range(-2,3)*2
j= [-1]*5 + [1]*5
pl.plt.scatter(i,j,s=sw,cmap=pl.plt.cm.bone)
pl.plt.show()
