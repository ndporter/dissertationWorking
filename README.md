# dissertationWorking
Files related to Nathaniel D. Porter dissertation on book copurchase networks
*****
This is a working repository for code (primarily Python) related to my dissertation project. Contents are not licensed for reuse at this time, but feel free to report an issue or send a pull request if you have questions or would like to adapt it.

Master directory is primarily data preparation (scraping and combining) relevant to multiple chapters. It does not duplicate code from the chapter directories.

Note that as this is primarily for me, no data are included and some code will reference local directories on my PC. Dissertation proposal is included for reference purposes only; some procedures have subsequently changed.

See below for progress and notes.

*****
# Status
Overall tasks:
-Upgrade code to Python 3 and troubleshoot

Master:
-Successfully extracts networks and most attribute data to csv
-Verify all relevant attributes are consistently extracted without hand-munging for non-English characters (upgrading to Python 3 may solve)

Chapter 1:
-Successful preliminary supervised learning models (SVM/SGD/Ridge) for subset of cases
-SVM rank model needs revision/replacement to reduce computational complexity
-cluster_with_LDA was combined with supplemental data to assign items to Evangelical or Mainline religious traditions; it may be superseded by forthcoming improvements in extraction scripts

Chapters 2-3:
-Pending
