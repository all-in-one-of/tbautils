import sys
import os
import math
import hou
import bson
import datetime
import xml.etree.ElementTree as ET
import tbautils.common

sys.dont_write_bytecode = True  # Avoid writing .pyc files

def local_update(majorUpdate=True):
    pass

def get_hda_version(hdaName):
    # try and extract version
    splits = hdaName.split('::')

    if '::' in hdaName:
        hdaVersion = float(splits[-1])
        hdaBaseName = '::'.join(splits[:-1])

        return hdaBaseName, hdaVersion

    print('Could not extract version number from HDA. Initialising it as version 0.1')
    hdaVersion = 0.1
    hdaBaseName = '::'.join(splits[:-1])

    return hdaBaseName, hdaVersion

def checkout_hda(ui, majorUpdate=True):
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
    hdaFilename = os.path.basename(hdaPath)
    hdaName = definition.nodeTypeName()

    # staging dir (using users otl dir for now)
    user_dir = hou.getenv('HOUDINI_USER_PREF_DIR')
    local_hda_dir = os.path.join(user_dir, 'otls')

    if not local_hda_dir:
        print('Could not find user otls directory at: {0}'.format(local_hda_dir))
        return

    newHdaPath = os.path.abspath(os.path.join(local_hda_dir, hdaFilename)).replace('\\','/')

    # try and extract version
    hdaBaseName, hdaVersion = get_hda_version(hdaName)

    # open file permissions
    os.chmod(hdaPath, 0o700)

    # if newHdaPath exists
    # get latest version of local definition and version up
    # else version up
    if os.path.exists(newHdaPath):
        print('Found existing hda here: {}'.format(newHdaPath))
        print('Finding local definition version and versioning up based on that')

        # last one should be latest version (otherwise we could loop through and get their versions)
        local_definition = hou.hda.definitionsInFile(newHdaPath)[-1]

        print('Local definitions')
        print(local_definition)
        print('Local version: {}'.format(local_definition.nodeTypeName()))

        # try and extract version
        hdaBaseName, localVersion = get_hda_version(hdaName)
        hdaVersion = max(hdaVersion, localVersion)

        # save current node
        definition.updateFromNode(node)

    if majorUpdate:
        newVersion = str(math.ceil(hdaVersion+0.01))
    else:
        newVersion = str(hdaVersion + 0.1)

    newHdaName = '{0}::{1}'.format(hdaBaseName, newVersion)

    print('oldHdaPath: {}'.format(hdaPath))
    print('oldHdaName: {}'.format(hdaName))
    print('oldVersion: {}'.format(hdaVersion))

    print('newHdaPath: {}'.format(newHdaPath))
    print('newHdaName: {}'.format(newHdaName))
    print('newVersion: {}'.format(newVersion))

    # copy the file to the users local directory
    definition.copyToHDAFile(newHdaPath, newHdaName)
    definition = hou.hda.definitionsInFile(newHdaPath)[-1]

    # save new definition
    definition.updateFromNode(node)

    # install new hda to houdini session
    hou.hda.installFile(newHdaPath)

    # change selection to use new hda
    node = node.changeNodeType(newHdaName, keep_network_contents=False)

    # open asset for editing
    node.allowEditingOfContents()

    # set permission to writeable by you
    os.chmod(newHdaPath, 0o700)

    # close ui
    ui.close()


def publish_hda(ui, location='job', majorUpdate=True):
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
    hdaName = node.type().name()
    hdaPath = definition.libraryFilePath() # //TBA-AD/redirect$/mike.battcock/Documents/houdini16.5\otls\tba_c.hda
    hdaFileName = os.path.basename(hdaPath)

    # try and extract version
    hdaBaseName, hdaVersion = get_hda_version(hdaName)

    # open file permissions
    os.chmod(hdaPath, 0o700)

    # get major, minor and build numbers from houdini version
    major, minor, build = hou.applicationVersionString().split('.')

    # published dir
    if location == 'job':
        job_data = tbautils.common.parse_job_path(hou.hipFile.path())

        if not job_data['job']:
            hou.ui.displayMessage('You are not currently working in a job.')
            return

        config_dir = os.path.join(job_data['job_path'], 'config')
        # might need to check for this folder first since if we need to recreate it it needs to be a hidden folder
        publish_dir = os.path.join(config_dir, 'houdini', 'otls')

        if not os.path.exists(publish_dir):
            os.makedirs(publish_dir)
    elif location == 'build/shot':
        job_data = tbautils.common.parse_job_path(hou.hipFile.path())

        if not job_data['entity']:
            hou.ui.displayMessage('You are not currently working in build or shots.')
            return

        # might need to check for this folder first since if we need to recreate it it needs to be a hidden folder
        publish_dir = os.path.join(job_data['job_path'], 'vfx', job_data['stage'], job_data['entity'], '_published3d', 'otls')

        if not os.path.exists(publish_dir):
            os.makedirs(publish_dir)
    elif location == 'site':
        publish_dir = os.path.join('S:/3D_globalSettings/houdini/' + major + '.' + minor, 'otls')
    else:
        print('Location parameter is invalid. Must be either shot, job or site')
        return

    if not os.path.exists(publish_dir):
        print('Publish directory does not exist: {}'.format(publish_dir))
        hou.ui.displayMessage('Publish directory does not exist: {}'.format(publish_dir))
        return

    newHdaPath = os.path.abspath(os.path.join(publish_dir, hdaFileName)).replace('\\','/')

    if newHdaPath == hdaPath:
        print('HDA is already published. Checkout first if you want to make changes')
        hou.ui.displayMessage('HDA is already published. Checkout first if you want to make changes')
        return

    # resolve conflicts and get highest version
    if os.path.exists(newHdaPath):
        print('Conflicting hda: {}'.format(newHdaPath))
        print('Finding conflicting definition version and versioning up based on that')

        # last one should be latest version (otherwise we could loop through and get their versions)
        #conflicting_definition = hou.hda.definitionsInFile(newHdaPath)[-1]

        conflicting_definition = sorted(hou.hda.definitionsInFile(newHdaPath), key=lambda x: float(x.nodeTypeName().split('::')[-1]))[-1]
        #conflicting_definition = sorted(hou.hda.definitionsInFile(newHdaPath), key=lambda x: x.nodeTypeName())[-1]
        #print "sorted defs: {}".format(flt_defs[-1])

        conflicting_hdaName = conflicting_definition.nodeTypeName()

        print('Conflicting hdaName: {}'.format(conflicting_hdaName))


        # try and extract version
        hdaBaseName, conflicting_version = get_hda_version(conflicting_hdaName)
        print('Conflicting version: {}'.format(conflicting_version))
        print "hdaVersion".format(hdaVersion)
        hdaVersion = max(hdaVersion, conflicting_version + 1)

    # save current node
    definition.updateFromNode(node)

    """
    if majorUpdate:
        newVersion = str(math.ceil(hdaVersion+0.01))
    else:
        newVersion = str(hdaVersion + 0.1)
    """

    #newName = hdaName

    newName = '{}::{}'.format(hdaBaseName, hdaVersion)

    print ""
    print('oldHdaPath: {}'.format(hdaPath))
    print('oldName: {}'.format(hdaName))

    print('newHdaPath: {}'.format(newHdaPath))
    print('newName: {}'.format(newName))

    # copy the file to the published directory
    os.chmod(hdaPath, 0o700)
    definition.copyToHDAFile(str(newHdaPath), str(newName))

    # install new hda to houdini session
    hou.hda.installFile(newHdaPath)
    # change selection to use new hda
    node = node.changeNodeType(newName, keep_network_contents=False)

    # match current definition to lock asset
    #node.matchCurrentDefinition()

    # check if filepath clash

    # set file to read only
    os.chmod(newHdaPath, 0o444)

    # Add asset to database
    db_update_asset(node)

    # close ui
    ui.close()


def db_update_asset(node):
    """ Add the HDA definition attached to 'node' to the database.
    """

    db = tbautils.common.getDB()

    # Initialize variables
    asset_type = None
    parent_id = None
    parent_asset = None
    existing = None

    # Try to get attached asset type
    try:
        asset_type = node.parm('asset_type').evalAsString()
    except:
        asset_type = ''

    # Get parent_asset if it exists
    try:
        parent_id = node.parm('parent_asset_id').eval()
    except:
        parent_id = None

    if parent_id:
        parent_asset = db.assets_curr.find_one({ "_id": bson.ObjectId(parent_id) })

        # Search for existing assets of our type attached to parent
        search = {
            'name': parent_asset['name'],
            'stage': parent_asset['stage'],
            'entity': parent_asset['entity'],
            'type': asset_type
        }

        existing = db.assets_curr.find_one(search)


    lib_filepath = node.type().definition().libraryFilePath()
    latest_version = float(node.type().name().split('::')[-1])

    if existing:
        """ Move current existing asset entry to assets_prev if exisitng
        asset is in assets_curr
        """
        print "CASE 1"
        old_id = existing['_id']
        del existing['_id']
        db.assets_prev.insert(existing)
        db.assets_curr.update_one(
            { '_id': bson.ObjectId(old_id) },
            { '$set': {
                'version': latest_version,
                'dateCreated': datetime.datetime.utcnow(),
                'filepath': lib_filepath,
                'author': os.environ['USERNAME']
            }}
        )
        hou.ui.displayMessage("Updated asset to version {}".format(latest_version))

    elif not existing and parent_asset:
        """ If there is no previous version but parent_asset data is
        attached, then insert new entry into assets_curr with data
        derived from parent_asset.
        """
        print "CASE 2"
        new_asset = parent_asset
        del new_asset['_id']
        new_asset['type'] = asset_type
        new_asset['version'] = 1
        new_asset['author'] = os.environ['USERNAME']
        new_asset['filepath'] = lib_filepath,
        new_asset['dateCreated'] = datetime.datetime.utcnow()
        db.assets_curr.insert(new_asset)
        hou.ui.displayMessage("Installed new asset into database!")

    else:
        """ If no existing version or parent_asset data found, then 
        create entirely new asset entry.
        New need to get the following information:
        * job_id
        * entity
        * type
        * stage
        * name
        """
        print "CASE 3"
        path_data = tbautils.common.parse_job_path(hou.hipFile.path())
        job = db.jobs.find_one({ "name": path_data['job'] })

        new_asset = {
            'name': '',
            'version': 1,
            'author': os.environ['USERNAME'],
            'filepath': lib_filepath,
            'dateCreated': datetime.datetime.utcnow(),
            'job_id': bson.ObjectId(job['_id']),
            'stage': path_data['stage'],
            'entity': path_data['entity']
        }

        db.assets_curr.insert(new_asset)
        hou.ui.displayMessage("Installed new asset into database!")


def create_hda(ui, name, min_inputs=1, max_inputs=1, major=0, minor=1):
    print('TBA :: local_hda')

    node = hou.selectedNodes()

    if not node:
        print('First select the subnet you want to turn into an HDA')
        return

    user_dir = hou.getenv('HOUDINI_USER_PREF_DIR')

    if not user_dir:
        print('Could not find user directory at: {0}'.format(user_dir))
        return

    # one at a time..
    node = node[0]

    nodeType = node.type()

    if nodeType.name() != 'subnet':
        print('Selection is not a subnet')
        return

    # try and enforce name
    name = name.replace('TBA_','')
    name = name.replace('tba_','')

    # name of node when created in houdini
    label = 'TBA_{}'.format(name)
    # spaces can exist in the label but not any other names
    name = name.replace('_','')
    # hda name with versioning namespace
    hda_name = 'tba_{}::0.1'.format(name.lower())
    # filename on disk
    filename = 'tba_{}.hda'.format(name.lower())

    local_hda_dir = os.path.join(user_dir, 'otls')

    # make local folder if doesnt exist
    if not local_hda_dir:
        print('Creating local otls folder: {0}'.format(local_hda_dir))
        os.mkdir(local_hda_dir)

    hdaPath = os.path.join(local_hda_dir, filename)

    if not node.canCreateDigitalAsset():
        print('Not able to create digital asset')
        return

    print('Create hda at: {0}'.format(hdaPath))

    # show progress window
    operation = hou.InterruptableOperation('TBA :: Creating HDA', long_operation_name='Creating HDA', open_interrupt_dialog=True)

    operation.__enter__()

    num_tasks = 3
    percent = 1.0 / num_tasks

    # rename subnet. This will be used for the asset label
    node.setName(label)

    hda = node.createDigitalAsset(name=hda_name,
                                hda_file_name=hdaPath,
                                min_num_inputs=min_inputs,
                                max_num_inputs=max_inputs,
                                version='0.1')

    # update progress
    operation.updateLongProgress(percent, 'Creating HDA')

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

    # update progress
    operation.updateLongProgress(percent, 'Finished')

    # Stop the operation. This closes the progress bar dialog.
    operation.__exit__(None, None, None)

    # open file permissions
    os.chmod(hdaPath, 0o700)

    # close ui
    ui.close()
