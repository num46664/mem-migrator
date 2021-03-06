from pymongo import MongoClient
from bson.objectid import ObjectId
from pprint import pprint
from functools import reduce
from datetime import datetime
import time
import os


LOCAL = False
TESTING_LIMIT = None
FILENAME = "log.txt"

if os.path.exists(FILENAME):
    os.remove(FILENAME)
def write(s):
    with open(FILENAME,'a+') as f:
        f.write(str(s) + '\n')

if LOCAL:
    client = MongoClient()
else:
    mongo_host = os.environ['MONGODB_SERVICE_HOST'] + ':' + os.environ['MONGODB_SERVICE_PORT']
    write(mongo_host)
    client = MongoClient(host=mongo_host,username="admin",password=os.environ['MONGODB_ADMIN_PASSWORD'])
write(client.admin.command('ismaster'))
# write(client.list_database_names())
db = client.mem if LOCAL else client.esm
documents = db.documents.find({'$or':[{"collections":[]},{"collections":None}]},{"_id":1,"projectFolderType":1,"projectFolderSubType":1,"displayName":1,"project":1,"directoryID":1})
# documents = list(documents)
# # documents = db.documents.find({"directoryID":32,"project":ObjectId("582244166d6ad30017cd47e1")},{"_id":1,"projectFolderType":1,"projectFolderSubType":1,"displayName":1,"project":1,"directoryID":1})
# write(len(documents))
# # write(list(documents)[:10])
# # map(lambda d: write(d['displayName']),list(documents)[:10])
# write(len(documents))
guess_data = {}


def make():
    collections = {}
    count = 0
    for doc in documents:
        # write(str(count) + doc['displayName'])
        col_doc_id = db.collectiondocuments.insert_one({
            "document" : doc['_id'],
            "_schemaName" : "Collectiondocument",
            "userCan" : {
                "delete" : False,
                "write" : False,
                "read" : False
            },
            "isPublished" : False,
            "delete" : [
                "sysadmin"
            ],
            "write" : [
                "sysadmin"
            ],
            "read" : [
                "sysadmin"
            ],
            "addedBy" : ObjectId("582243a76d6ad30017cd3ed6"),
            "dateUpdated" : datetime.now(),
            "sortOrder" : int(time.time() * 1000),
            "updatedBy" : ObjectId("582243a76d6ad30017cd3ed6"),
            "dateAdded" : datetime.now()
        }).inserted_id

        folderName = db.folders.find_one({'project':doc['project'],'directoryID':doc['directoryID']})['displayName']

        count += 1
        key = str(doc['project']) + str(doc['directoryID'])
        if key in collections:
            collections[key]['otherDocuments'].append(col_doc_id)
            guess_data[key].append(doc['displayName'])
        else:
            collections[key] = {
                                    "_schemaName" : "Collection",
                                    "userCan" : {
                                        "unPublish" : True,
                                        "publish" : True,
                                        "delete" : True,
                                        "write" : True,
                                        "read" : True
                                    },
                                    "isPublished" : False,
                                    "delete" : [
                                        "sysadmin",
                                    ],
                                    "write" : [
                                        "sysadmin",
                                    ],
                                    "read" : [
                                        "sysadmin",
                                        "public"
                                    ],
                                    "displayName":folderName,
                                    "isForMEM" : True,
                                    "isForENV" : False,
                                    "otherDocuments" : [],
                                    "mainDocuments": [col_doc_id],
                                    "date" : datetime.now(),
                                    "description" : "",
                                    "addedBy":ObjectId("582243a76d6ad30017cd3ed6"),
                                    "updatedBy" : ObjectId("582243a76d6ad30017cd3ed6"),
                                    "dateUpdated" : datetime.now(),
                                    "dateAdded" : datetime.now(),
                                    "project" : doc['project'],
                                    "hasPublished" : True
                                }
            guess_data[key] = [doc['displayName']]
        
        
        # if 'displayName' not in collections[key]: 
        #     if 'projectFolderSubType' in doc:
        #         collections[key]['displayName'] = doc['projectFolderSubType']
        #     elif: 'projectFolderType' in doc:
        #         collections[key]['displayName'] = doc['projectFolderType']

        if count == TESTING_LIMIT:
            break
    write(str(count) + ' count')
    write(str(len(collections)) + ' Collections Created')
    for key,collection in collections.items():
        if 'displayName' not in collection:
            collection['displayName'] = 'Untitled'
        collection['parentType'] = guess_type(key)
        update(collection)

def update(collection):
    write('___________________________________')
    write('collection: ' + collection["displayName"])
    write('type:       ' + collection["parentType"])
    pname = ""
    try:
        pname = db.projects.find({"_id":collection["project"]})[0]["name"]
    except Exception:
        pname = "Error"
    write('project:    ' + pname)
    write('documents:')
    col_id = db.collections.insert_one(collection).inserted_id
    for col_doc_id in collection['otherDocuments'] + collection['mainDocuments']:
        doc_id = db.collectiondocuments.find_one({'_id':col_doc_id})['document']
        write('            ' + db.documents.find({'_id':doc_id})[0]['displayName'])
        db.documents.update_one({'_id':doc_id},{'$push':{'collections':col_id}})
    
def guess_type(key):
    # keywords corresponding to different types
    keywords = (("Authorizations",["amendment","authorizing","approving","approval",'authorization',"permit"]),("Compliance and Enforcement",["inspection",""]))
    counter = {}
    # write(guess_data[key])
    # count word occurences
    for words in guess_data[key]:
        for word in words.split(' '):
            if word.lower() in counter:
                counter[word.lower()] += 1
            else: counter[word.lower()] = 1

    # create counts of keywords related to types
    type_counts = [(_type,sum(map(lambda w: counter[w] if w in counter else 0,words))) for (_type,words) in keywords]
    # if no keywords appear, guess that type is "Other"
    # write(type_counts)
    if sum(list(zip(*type_counts))[1]) == 0:
        return "Other"
    # otherwise type is the one with largest number of keyword matches
    else: return reduce(lambda x,y: x if x[1] > y[1] else y, type_counts)[0]       

make()
if not LOCAL:
    while True:
        continue