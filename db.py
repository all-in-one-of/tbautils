import sys
import os

path = '//prospero/apps/utilities/Python27/Lib/site-packages'

if path not in sys.path:
    sys.path.append(path)

from pymongo import MongoClient

sys.dont_write_bytecode = True  # Avoid writing .pyc files

class db():
    client = None
    db = None

    def __init__(self, host='tbavm1', port=27017, db_name='tag_model'):
        self.client = MongoClient(host, port)
        self.db = self.client[db_name]

    def get_job_by_name(self, job_name):
        return self.db.jobs.find_one({'name':job_name})

    def export_asset(self, new_asset):
        print('tba_utils - export asset')

        # get job tags
        #job_tags =

        # copy current asset to assets_prev
        asset_curr = self.db.assets_curr.find_one({
            'name':new_asset['name'],
            'stage':new_asset['stage'],
            'entity':new_asset['entity']
        })

        if asset_curr:
            asset_curr_id = asset_curr['_id']
            del asset_curr['_id']

            asset_id = self.db.assets_prev.insert_one(asset_curr).inserted_id

            print('tba_utils - Moving {} asset_curr to asset_prev'.format(new_asset['name']))
            print('tba_utils - asset_curr id {}'.format(asset_curr_id))

            # update asset_curr
            self.db.assets_curr.update({ '_id': asset_curr_id }, new_asset)
        else:
            asset_id = self.db.assets_curr.insert_one(new_asset).inserted_id

# create class instance
db = db()
