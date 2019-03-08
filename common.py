import os
import sys

sys.dont_write_bytecode = True  # Avoid writing .pyc files

def parse_job_path(path):
    # initialize all to empty string
    job = stage = entity = task = job_path = ''

    sceneDirNames = [
        'hip',
        'scene',
        'scenes'
    ]

    # os.sep doesn't appear to work with hou.hipFile
    #parts = path.split(os.sep)
    parts = path.split('/')

    if 'vfx' in parts:
        vfx_index = parts.index('vfx')

        job = parts[vfx_index - 1]
        stage = parts[vfx_index + 1]
        entity = parts[vfx_index + 2]
    else:
        print("VFX directory not found. Some data is missing")

    # work backwards..
    scene = parts[-1]
    # 'task' should be parent directory of the scene
    task = parts[-2]
    # ignore it if that folder is a scenes directory
    if task.lower() in sceneDirNames:
        task = ''

    return {
        'job': job,
        'stage': stage,
        'entity': entity,
        'task': task,
        'job_path': os.sep.join(parts[:vfx_index])
    }


def getDB():
    import pymongo
    import config
    client = pymongo.MongoClient(config.mongo['hostname'], config.mongo['port'])
    db = client['tag_model']
    return db

#
# Get job by id. Needs to be fixed as it should really be using getDB().
#
def getJob(id):
    import bson
    import pymongo
    import config
    client = pymongo.MongoClient(config.mongo['hostname'], config.mongo['port'])
    db = client['tag_model']
    query = db.jobs.find_one({"_id": bson.ObjectId(id)})
    return query