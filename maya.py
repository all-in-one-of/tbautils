import os
import getpass
import datetime

import maya.cmds as mc

from tbautils import common

sys.dont_write_bytecode = True  # Avoid writing .pyc files

## ASSETS ##
def get_tba_assets():
    tba_sets = mc.ls('tba_asset*', type='objectSet')

    tba_assets = []

    for tba_set in tba_sets:
        asset = {}

        # populate string attributes
        for attr in ['name', 'type', 'stage', 'entity', 'author', 'dateCreated', 'dateUpdated', 'version', 'tags']:
            asset[attr] = mc.getAttr(tba_set + '.' + attr)

        tba_assets.append(asset)

    return tba_assets

def create_tba_assets():
    # get maya selection
    sel = mc.ls(sl=1, transforms=1)

    if not sel:
        print('Selection must be transform nodes')
        return []

    # get environment data
    scene = get_scene_path()

    data = tba_utils.parse_job_path(scene)
    job_doc = tba_utils.db.get_job_by_name(data['job'])

    print('Data is {}'.format(data))

    tba_assets = []

    for obj in sel:
        # selected must be a group (cant have any child shapes)
        shapes = mc.listRelatives(obj, shapes=1)

        if shapes:
            print('Skipping {0} since it is not a group node'.format(obj))
            continue

        # strip grp from name
        assetName = obj.split('|')[-1]
        assetName = assetName.lower().split('grp')[0].rstrip('_')

        # create asset object
        asset = {
            'job_id': job_doc['_id'],
            'name': assetName,
            'type': data['task'],
            'version': 0,
            'stage': data['stage'],
            'entity': data['entity'],
            'tags': [],
            'author': getpass.getuser(),
            'dateCreated': datetime.datetime.utcnow(),
            'dateUpdated': datetime.datetime.utcnow()
        }

        tbaSet = 'tba_asset_' + assetName

        # ignore if set already exists
        if mc.objExists(tbaSet):
            continue

        tbaSet = mc.sets(obj, name=tbaSet)
        tba_assets.append(asset)

        # set string attributes on maya set
        for attr in ['name', 'job_id', 'type', 'stage', 'entity', 'author', 'dateCreated', 'dateUpdated']:
            mc.addAttr(tbaSet, longName=attr, dataType='string')
            mc.setAttr(tbaSet + '.' + attr, asset[attr], type='string')

        # set tags
        mc.addAttr(tbaSet, longName='tags', dataType='stringArray')
        mc.setAttr(tbaSet + '.tags', 0, type='stringArray')

        # set version
        mc.addAttr(tbaSet, longName='version', attributeType='byte')
        mc.setAttr(tbaSet + '.version', 0)

        # lock set so it cant be renamed
        #mc.lockNode( tbaSet )

    return tba_assets

def update_tba_asset(asset):
    print('update_tba_asset')
    tbaSet = mc.ls('tba_asset_' + asset['name'], type='objectSet')

    print('tbaSet: {}'.format(tbaSet))

    if not tbaSet:
        print('tba_asset_' + asset['name'] + ' does not exist')
        return

    tbaSet = tbaSet[0]

    # set string attributes on maya set
    for attr in ['name', 'type', 'stage', 'entity', 'author', 'dateUpdated']:
        mc.setAttr(tbaSet + '.' + attr, asset[attr], type='string')

    mc.setAttr(tbaSet + '.version', asset['version'])

def get_set_contents(name):
    print('tba_maya_api - get_set_contents')
    # get corresponding set
    tba_set = mc.ls('tba_asset_' + name, type='objectSet')

    if not tba_set:
        return False

    # get set contents
    objs = mc.sets( tba_set, q=True )

    if not objs:
        return False

    return objs

## END ASSETS ##

## FILE ##
def get_scene_path():
    return os.path.abspath(mc.file(q=1, sn=1))


## ABC ##
def export_abc(asset):
    '''
    param: asset [asset] - asset to be exported
    return: success - filepath
    '''

    tba_set = 'tba_asset_' + asset['name']

    rootObjs = get_set_contents(asset['name'])

    if not rootObjs:
        print('TBA set does not contain any valid objects')
        return

    data = tba_utils.parse_job_path(get_scene_path())
    publish_path = os.path.join(data['job_path'], 'vfx', data['stage'], '_published3d')
    task_path = os.path.join(publish_path, asset['name'], asset['type'])

    if not os.path.exists(task_path):
        os.makedirs(task_path)
        latest_version = 0
    else:
        # find latest version on disk and version up
        versions = os.listdir(task_path)

        if len(versions) == 0:
            latest_version = 0
        else:
            versionStr = sorted(versions)[-1]
            latest_version = int(versionStr[1:])

    asset['version'] = latest_version + 1
    version = 'v' + str(latest_version + 1).zfill(3)

    export_path = os.path.join(task_path, version)

    if not os.path.exists(export_path):
        os.makedirs(export_path)

    asset['filepath'] = os.path.join(export_path, asset['name'] + '.abc' )
    asset['dateUpdated'] = datetime.datetime.utcnow()

    root = ''

    for obj in rootObjs:
        root += ' -root ' + obj

    command = '-uvWrite -worldSpace{0} -file {1}'.format(root, asset['filepath'])

    mc.AbcExport ( jobArg = command )

    # update maya set

    update_tba_asset(asset)

    return asset
