import sys
import os
import re
import hou
import bson
import datetime
import xml.etree.ElementTree as ET
import common
from stat import S_IREAD, S_IRGRP, S_IROTH


sys.dont_write_bytecode = True  # Avoid writing .pyc files

def checkout_hda():
    # copy hda to local directory
    # install hda (this will set it as the active hda in houdini)
    # set allow editing of contents

    node = hou.selectedNodes()

    if not node:
        print('First select an HDA you want to publish')
        return

    node = node[0]

    # get definition
    definition = node.type().definition()

    if not definition:
        print('Selected node is not an HDA')
        return

    # get filepath to hda file
    hdaPath = definition.libraryFilePath()

    # staging dir (using users otl dir for now)
    user_dir = hou.getenv('HOUDINI_USER_PREF_DIR')

    if not user_dir:
        print('Could not find user directory at: {0}'.format(user_dir))
        return

    local_hda_dir = os.path.join(user_dir, 'otls')

    # get basename
    basename = os.path.basename(hdaPath)

    newHdaPath = os.path.join(local_hda_dir, basename)

    # check if newHdaPath exists - it shouldnt if the user has only used these tools
    if os.path.exists(newHdaPath):
        print('Local HDA already exists with path: {0}'.format(newHdaPath))
        return

    # copy the file to the published directory
    definition.copyToHDAFile(newHdaPath)

    # install
    hou.hda.installFile(newHdaPath)

    # open asset for editing
    node.allowEditingOfContents()


def publish_hda(majorUpdate=True, location='job', filepath=None):
    '''
    param: majorUpdate [boolean] - Whether to do a major or minor version up
    param: location [string] - Where to publish the hda to ('shot', 'job', 'site')
    return: filepath to hda or false if unsuccessful
    '''
    node = hou.selectedNodes()

    if not node:
        print('First select an HDA you want to publish')
        return

    node = node[0]

    # get definition
    definition = node.type().definition()

    if not definition:
        print('Selected node is not an HDA')
        return

    # asset name
    hdaLabel = node.type().name()
    hdaPath = definition.libraryFilePath() # //TBA-AD/redirect$/mike.battcock/Documents/houdini16.5\otls\tba_c_1.0.hda
    hdaVersion = definition.version()

    # get major, minor and build numbers from houdini version
    major, minor, build = hou.applicationVersionString().split('.')

    # published dir
    if location == 'job':
        job_data = common.parse_job_path(hou.hipFile.path())
        config_dir = os.path.join(job_data['job_path'], 'config')
        # might need to check for this folder first since if we need to recreate it it needs to be a hidden folder
        publish_dir = os.path.join(config_dir, 'houdini', 'otls')

        if not os.path.exists(publish_dir):
            os.makedirs(config_dir)
    elif location == 'shot':
        job_data = common.parse_job_path(hou.hipFile.path())
        # might need to check for this folder first since if we need to recreate it it needs to be a hidden folder
        publish_dir = os.path.join(job_data['job_path'], 'vfx', job_data['stage'], job_data['entity'], '_published3d', 'otls')

        if not os.path.exists(publish_dir):
            os.makedirs(config_dir)
    elif location == 'site':
        publish_dir = os.path.join('S:/3D_globalSettings/houdini/' + major + '.' + minor, 'otls')
    else:
        print('Location parameter is invalid. Must be either shot, job or site')
        return

    print('Publish directory: {0}'.format(publish_dir))

    # check if selected asset is already published
    if publish_dir in hdaPath:
        print('Asset is already in the published directory. Check it out if you want to make changes')
        return

    basename = os.path.splitext(os.path.basename(hdaPath))[0]

    try:
        parts = basename.split('_')
        curVersion = float(parts[-1])
    except:
        print('Could not extract the version number from the hda....: {0}'.format(str(curVersion)))
        return

    if majorUpdate:
        newVersion = curVersion + 1.0
    else:
        newVersion = curVersion + 0.1

    # rebuild filename
    filename = '_'.join(parts[:-1]) + '_' + str(newVersion) + '.hda'

    # Choose whether to use default generated filepath, or the path
    # passed as an argument to this function
    if filepath is None:
        newHdaPath = os.path.join(publish_dir, filename)
    else:
        newHdaPath = filepath

    #if os.path.exists(newHdaPath):
    #    print('Filepath already exists.. {0}'.format(newHdaPath))

    # copy the file to the published directory
    try:
        definition.copyToHDAFile(newHdaPath)
    except hou.OperationFailed:
        print "Could not write HDA to {}. Check permissions or if it already exists.".format(newHdaPath)

    # install new hda to houdini session
    try:
        hou.hda.installFile(newHdaPath)
    except hou.OperationFailed:
        print "Could not install HDA. Is it already in the scene?"

    # change selection to use new hda
    #node.changeNodeType(newVersion, keep_network_contents=False)

    # match current definition to lock asset
    node.matchCurrentDefinition()

    # set file to read only
    try:
        os.chmod(newHdaPath, S_IREAD|S_IRGRP|S_IROTH)
    except:
        print "Could not set permissions on {}".format(newHdaPath)

    return newHdaPath


def create_hda(label, name, min_inputs=0, max_inputs=0, major=0, minor=0):
    print('TBA :: local_hda')

    node = hou.selectedNodes()

    if not node:
        print('First select the subnet you want to turn into an HDA')
        return

    # one at a time..
    node = node[0]

    nodeType = node.type()

    if nodeType.name() != 'subnet':
        print('Selection is not a subnet')
        return

    user_dir = hou.getenv('HOUDINI_USER_PREF_DIR')

    if not user_dir:
        print('Could not find user directory at: {0}'.format(user_dir))
        return

    local_hda_dir = os.path.join(user_dir, 'otls')

    # make local folder if doesnt exist
    if not local_hda_dir:
        print('Creating local otls folder: {0}'.format(local_hda_dir))
        os.mkdir(local_hda_dir)

    versionStr = str(major) + '.' + str(minor)
    assetName = 'tba::' + str(name) + '::' + versionStr
    filename = 'tba_' + str(name) + '_' + versionStr + '.hda'
    filepath = os.path.join(local_hda_dir, filename)

    print('Create hda at: {0}'.format(filepath))

    if not node.canCreateDigitalAsset():
        print('Not able to create digital asset')
        return

    # rename subnet. This will be used for the asset label
    node.setName(name)

    hda = node.createDigitalAsset(name=label,
                                hda_file_name=filepath,
                                min_num_inputs=min_inputs,
                                max_num_inputs=max_inputs,
                                version=versionStr)

    user = hou.getenv('USER')
    #node.setComment('Created by: {0}'.format(user))
    hda.setUserData('user',user)

    # get hda definition
    hdaDefinition = hda.type().definition()

    # get all parameters
    template_group = hda.parmTemplateGroup()
    # copy to hda
    hdaDefinition.setParmTemplateGroup(template_group)

    # set tool sub menu to TBA
    tool = '''<?xml version="1.0" encoding="UTF-8"?>
    <shelfDocument>
        <tool name="$HDA_DEFAULT_TOOL" label="$HDA_LABEL" icon="$HDA_ICON">
            <toolMenuContext name="viewer">
                <contextNetType>OBJ</contextNetType>
            </toolMenuContext>
            <toolMenuContext name="network">
                <contextOpType>$HDA_TABLE_AND_NAME</contextOpType>
            </toolMenuContext>
            <toolSubmenu>TBA</toolSubmenu>
            <script scriptType="python"><![CDATA[import objecttoolutils
objecttoolutils.genericTool(kwargs, '$HDA_NAME')]]></script>
        </tool>
    </shelfDocument>'''

    hdaDefinition.addSection('Tools.shelf', tool)

    # set file to read only
    #os.chmod(filepath, 0o777)


#
# Create lookdev HDA wrapper
#
def create_lookdev_hda(sel):
    db = common.getDB()

    parent_parms = {
        'name': 'parent_asset_name',
        'stage': 'parent_asset_stage',
        'entity': 'parent_asset_entity',
    }

    # Test if there is something selected
    if sel is None:
        hou.ui.displayMessage('No node selected')
        exit

    # Filter parms to what is defined in parent_parms
    f_parms = {x.name():x.eval() for x in sel.parms() if x.name() in parent_parms.values()}

    # Check if all required parms are present
    if not all(x in f_parms.keys() for x in parent_parms.values()):
        hou.ui.displayMessage('Not all parent asset details detected!')
        exit

    # See if asset exists in db
    query = db.assets_curr.find_one({
        "name":     f_parms['parent_asset_name'],
        "stage":    f_parms['parent_asset_stage'],
        "entity":   f_parms['parent_asset_entity'],
        "type":     'shader'
    })

    # Default to version 1
    version = 1

    # If we find a matching asset, grab its version
    if query:
        version = query['version'] + 1

    create_hda(
        'tba::{}_model_lookdev::{}'.format(f_parms['parent_asset_name'], version),
        '{}_model_lookdev'.format(f_parms['parent_asset_name']),
        major=version
    )

    hou.ui.displayMessage("Asset created")


#
# Publish lookdev HDA wrapper for publish_hda
#
def publish_lookdev_hda(sel):

    if sel is None:
        hou.ui.displayMessage("No node selected", severity=hou.severityType.Error)
        exit

    if sel.parm('parent_asset_job_id') is None:
        hou.ui.displayMessage("No job attached to asset", severity=hou.severityType.Error)
        exit

    if sel.parm('parent_asset_id') is None:
        hou.ui.displayMessage("No parent ID attached to asset", severity=hou.severityType.Error)
        exit

    job = common.getJob(sel.parm('parent_asset_job_id').evalAsString())

    # Get DB
    db = common.getDB()

    # Get parent_asset
    parent_asset = db.assets_curr.find_one({ "_id": bson.ObjectId(sel.parm('parent_asset_id').eval()) })

    # Search for existing shaders attached to parent
    search = {
        'name': parent_asset['name'],
        'stage': parent_asset['stage'],
        'entity': parent_asset['entity'],
        'type': 'shader'
    }

    existing = db.assets_curr.find_one(search)

    # Figure out latest version. If we're on v1, assume new shader entry
    local_version = int(sel.type().nameComponents()[-1])
    latest_version = 0
    if existing:
        latest_version = existing['version']

    print "Latest version: {}".format(latest_version)
        
    # If someone has already published a version to db and we are behind, update local
    # asset to latest version.
    if local_version <= latest_version:
        print "Local asset is behind latest asset!"
        latest_version += 1
        latest_name = '::'.join(list(sel.type().nameComponents()[1:-1]) + [str(latest_version)])
        print sel.type().definition().libraryFilePath()
        latest_file_dir = '/'.join(sel.type().definition().libraryFilePath().split('/')[:-1])
        latest_file_name = '{}/{}.0.hda'.format(latest_file_dir, latest_name.replace('::', '_'))
        print "Writing to: {}".format(latest_file_name)
        sel.type().definition().copyToHDAFile(latest_file_name, new_name=latest_name)
        hou.hda.installFile(latest_file_name)
        print "Installed {}".format(latest_file_name)
        sel = sel.changeNodeType(latest_name)
        print "Switched {} to {}".format(sel.name(), latest_name)
    else:
        latest_version = local_version

    print "LOCAL FILENAME: {}".format(sel.type().definition().libraryFilePath())
    lib_path = sel.type().definition().libraryFilePath()

    local_filename = list(filter(None, re.split('[\\\\/]', lib_path)))[-1]

    # Get job root and build HDA publish target

    publish_filepath = '{}/config/houdini/otls/{}'.format(job['path'], local_filename)

    sel.type().definition().updateFromNode(sel)
    print "Publishing HDA to {}".format(publish_filepath)


    r_filepath = publish_hda(majorUpdate=False, filepath=publish_filepath)

    # Check if publish_hda has returned a publish filepath
    if r_filepath is None:
        hou.ui.displayMessage("Asset publish has failed!", severity=hou.severityType.Error)
        exit

    #
    # Move current existing shader entry to assets_prev then update in place
    # the assets_curr
    #
    if existing:
        id = existing['_id']
        del existing['_id']
        db.assets_prev.insert(existing)
        db.assets_curr.update_one(
            { '_id': bson.ObjectId(id) },
            { '$set': {
                'version': latest_version,
                'dateCreated': datetime.datetime.utcnow(),
                'filepath': r_filepath,
                'author': os.environ['USERNAME']
            }}
        )

        hou.ui.displayMessage("Updated asset to version {}".format(latest_version))
    else:
        #
        # New asset, borrow from parent_asset entry
        #
        new_asset = parent_asset
        del new_asset['_id']
        new_asset['type'] = 'shader'
        new_asset['version'] = latest_version       # This should be 1 if our logic is sound.
        new_asset['author'] = os.environ['USERNAME']
        new_asset['filepath'] = r_filepath,
        new_asset['dateCreated'] = datetime.datetime.utcnow()
        db.assets_curr.insert(new_asset)
        hou.ui.displayMessage("Installed new asset into database!".format(latest_version))

    print "DONE!"



# Import Houdini Asset into the scene. Requires a pymongo database
# object and a unique object id (of the asset entry)
def importHoudiniAsset(db, obj_id):
    import hou
    import _alembic_hom_extensions as abc

    # Search assets_curr, then assets_prev for our obj_id
    asset = db.assets_curr.find_one({"_id": obj_id})

    if not asset:
        asset = db.assets_prev.find_one({"_id": obj_id})

    if asset:

        asset_name = '{}_{}'.format(asset['name'], asset['type'])
        assets_root = hou.node('/obj/ASSETS')

        if assets_root is None:
            assets_root = hou.node('/obj').createNode('subnet', 'ASSETS')

        asset_container = hou.node('/obj/ASSETS/{}'.format(asset_name))

        if asset_container is None:

            # Special case for layout
            if asset['type'] == 'layout':
                asset_node = assets_root.createNode('alembicxform', asset_name)
                asset_node.parm('fileName').set(asset['filepath'])
                obj_paths = [
                    x for i,x in enumerate(abc.alembicGetObjectPathListForMenu(str(asset['filepath'])))
                    if i % 2
                    and x is not  '/'
                ]
                asset_node.parm('objectPath').set(obj_paths[0])
                asset_connection = hou.node('/obj/ASSETS/{}_model'.format(asset['name']))

                # If model counterpart is not in scene, bring in model attached to layout
                if asset_connection is None:
                    asset_connection = importHoudiniAsset(db, asset['dep_model_id'])

                asset_connection.setInput(0, asset_node)
                assets_root.layoutChildren([asset_node, asset_connection])

            # Special case for shader
            elif asset['type'] == 'shader':
                hou.hda.installFile(asset['filepath'])
                defs = hou.hda.definitionsInFile(asset['filepath'])
                p_def = [x for x in defs if int(x.nodeType().nameComponents()[-1]) == asset['version']][0]
                hou.node('/out').createNode(p_def.nodeTypeName(), '{}_lookdev'.format(asset_name))
                print "Installed HDA {}".format(p_def.nodeTypeName())
            else:
                asset_container = assets_root.createNode('geo', asset_name)

                # Attach parent asset properties to asset node
                parent_properties = {
                    '_id':      'id',
                    'name':     'name',
                    'stage':    'stage',
                    'entity':   'entity',
                    'type':     'type',
                    'version':  'version',
                    'filepath': 'filepath',
                    'job_id':   'job_id'
                }

                pg = asset_container.parmTemplateGroup()
                fldr = hou.FolderParmTemplate(name='fldr_parent', label='Parent Asset', folder_type=hou.folderType.Tabs)

                for k,v in parent_properties.iteritems():
                    prm = hou.StringParmTemplate('parent_asset_{}'.format(v), v, 1)
                    prm.setDefaultValue([str(asset[k])])
                    prm.setDisableWhen("{{ parent_asset_{} != ''}}".format(k))
                    fldr.addParmTemplate(prm)

                pg.append(fldr)
                asset_container.setParmTemplateGroup(pg)
                asset_node = hou.node('/obj/ASSETS/{}/{}'.format(asset_name, asset_name))

                if asset_node is not None:
                    asset_node.destroy()

                asset_node = asset_container.createNode('alembic', asset_name)
                asset_node.parm('fileName').set(asset['filepath'])

        return asset_container